import json
import os
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiosqlite
from app.dependencies import get_current_user
from app.config import BASE_DIR, DATABASE

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))

@router.get("/incidents/my", response_class=HTMLResponse)
async def my_combined_requests(request: Request, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        # Получаем инциденты пользователя
        async with db.execute("""
            SELECT id AS incident_id, title, status, created_at
            FROM incidents
            WHERE reporter_id = ?
        """, (current_user['id'],)) as cursor:
            incidents = [dict(row) for row in await cursor.fetchall()]  # Преобразуем Row в словари

        # Для каждого инцидента получаем связанные услуги
        for incident in incidents:
            async with db.execute("""
                SELECT s.name, sci.quantity
                FROM service_cart_items sci
                JOIN services s ON sci.service_id = s.id
                WHERE sci.request_id = (
                    SELECT id FROM service_requests WHERE user_id = ? AND request_date = ?
                )
            """, (current_user['id'], incident['created_at'])) as cursor:
                incident['services'] = [dict(row) for row in await cursor.fetchall()]  # Преобразуем Row в словари

    return templates.TemplateResponse("my_incidents.html", {"request": request, "incidents": incidents, "user": current_user})



# Маршрут для просмотра списка всех инцидентов (для технической поддержки)
@router.get("/incidents", response_class=HTMLResponse)
async def all_incidents(request: Request, current_user: dict = Depends(get_current_user)):
    if current_user['role'] not in ['employee', 'admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row  # Устанавливаем row_factory
        async with db.execute("""
            SELECT
                i.id AS incident_id,
                i.title,
                i.status,
                i.created_at,
                u.username AS reporter_username
            FROM incidents i
            JOIN users u ON i.reporter_id = u.id
        """) as cursor:
            incidents = await cursor.fetchall()
    return templates.TemplateResponse("all_incidents.html", {"request": request, "incidents": incidents, "user": current_user})

# Маршрут для просмотра деталей инцидента
@router.get("/incidents/{incident_id}", response_class=HTMLResponse)
async def incident_detail(incident_id: int, request: Request, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row  # Устанавливаем row_factory
        async with db.execute("""
            SELECT
                i.id AS incident_id,
                i.title,
                i.description,
                i.status,
                i.created_at,
                i.updated_at,
                i.reporter_id,
                i.assignee_id,
                i.resolution_time,
                u.username AS reporter_username
            FROM incidents i
            JOIN users u ON i.reporter_id = u.id
            WHERE i.id = ?
        """, (incident_id,)) as cursor:
            incident = await cursor.fetchone()
        if not incident:
            raise HTTPException(status_code=404, detail="Инцидент не найден")
        # Проверка доступа
        if current_user['role'] not in ['employee', 'admin'] and incident['reporter_id'] != current_user['id']:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
    return templates.TemplateResponse("incident_detail.html", {"request": request, "incident": incident, "user": current_user})


# Маршрут для обновления статуса инцидента (для технической поддержки)
@router.post("/incidents/{incident_id}/update")
async def update_incident(
    incident_id: int,
    request: Request,
    status: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    if current_user['role'] not in ['employee', 'admin']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")
    async with aiosqlite.connect(DATABASE) as db:
        # Обновляем статус инцидента
        await db.execute("""
            UPDATE incidents SET status = ?, updated_at = datetime('now'), assignee_id = ?
            WHERE id = ?
        """, (status, current_user['id'], incident_id))
        # Если инцидент закрыт, вычисляем время решения
        if status == 'closed':
            async with db.execute("""
                SELECT julianday(updated_at) - julianday(created_at) FROM incidents WHERE id = ?
            """, (incident_id,)) as cursor:
                time_diff = await cursor.fetchone()
                resolution_time = int(time_diff[0] * 24 * 60)  # В минутах
            await db.execute("""
                UPDATE incidents SET resolution_time = ? WHERE id = ?
            """, (resolution_time, incident_id))
        await db.commit()
    return RedirectResponse(url=f"/incidents/{incident_id}", status_code=303)

@router.get("/combined-request", response_class=HTMLResponse)
async def combined_request_form(request: Request, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        # Отображаем только бизнес-услуги
        async with db.execute("""
            SELECT id, name, price, price_per 
            FROM services 
            WHERE category = 'business' AND is_active = 1
        """) as cursor:
            business_services = await cursor.fetchall()
    return templates.TemplateResponse("new_combined_form.html", {"request": request, "services": business_services, "user": current_user})




@router.post("/combined-request")
async def create_combined_request(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    selectedServices: list[int] = Form(...),  # Список ID выбранных услуг
    current_user: dict = Depends(get_current_user)
):
    async with aiosqlite.connect(DATABASE) as db:
        try:
            # Создаем инцидент
            await db.execute("""
                INSERT INTO incidents (title, description, status, created_at, updated_at, reporter_id)
                VALUES (?, ?, 'open', datetime('now'), datetime('now'), ?)
            """, (title, description, current_user['id']))

            # Получаем ID инцидента
            async with db.execute("SELECT last_insert_rowid()") as cursor:
                incident_id = (await cursor.fetchone())[0]

            # Проверяем выбранные услуги
            if selectedServices:
                # Создаем заявку на услуги
                await db.execute("""
                    INSERT INTO service_requests (user_id, request_date, status, total_price)
                    VALUES (?, datetime('now'), 'Pending', 0)
                """, (current_user['id'],))

                async with db.execute("SELECT last_insert_rowid()") as cursor:
                    request_id = (await cursor.fetchone())[0]

                total_price = 0
                for service_id in selectedServices:
                    # Убедимся, что услуга является бизнес-услугой
                    async with db.execute("""
                        SELECT price FROM services WHERE id = ? AND category = 'business'
                    """, (service_id,)) as cursor:
                        service = await cursor.fetchone()
                        if not service:
                            raise HTTPException(status_code=400, detail="Некорректная услуга.")
                        price = service[0]

                    # Добавляем услугу в заявку
                    await db.execute("""
                        INSERT INTO service_cart_items (request_id, service_id, quantity)
                        VALUES (?, ?, ?)
                    """, (request_id, service_id, 1))  # Количество по умолчанию = 1
                    total_price += price

                # Обновляем общую стоимость заявки
                await db.execute("""
                    UPDATE service_requests SET total_price = ? WHERE id = ?
                """, (total_price, request_id))

            await db.commit()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка создания заявки: {str(e)}")

    return RedirectResponse(url="/incidents/my", status_code=303)
