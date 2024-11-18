import os
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiosqlite
from app.dependencies import get_current_user
from app.config import BASE_DIR, DATABASE

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))

# Маршрут для создания нового инцидента (для рядовых сотрудников)
@router.get("/incidents/new", response_class=HTMLResponse)
async def new_incident(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("new_incident.html", {"request": request, "user": current_user})

@router.post("/incidents/new")
async def create_incident(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            INSERT INTO incidents (title, description, status, created_at, updated_at, reporter_id)
            VALUES (?, ?, 'open', datetime('now'), datetime('now'), ?)
        """, (title, description, current_user['id']))
        await db.commit()
    return RedirectResponse(url="/incidents/my", status_code=303)

# Маршрут для просмотра списка своих инцидентов (для рядовых сотрудников)
@router.get("/incidents/my", response_class=HTMLResponse)
async def my_incidents(request: Request, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row  # Устанавливаем row_factory
        async with db.execute("""
            SELECT id AS incident_id, title, status, created_at FROM incidents WHERE reporter_id = ?
        """, (current_user['id'],)) as cursor:
            incidents = await cursor.fetchall()
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
