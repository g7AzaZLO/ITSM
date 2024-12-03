import os
import logging
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiosqlite
from app.dependencies import get_current_user, role_required
from app.config import BASE_DIR, DATABASE

logger = logging.getLogger(__name__)
router = APIRouter()

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))

# Маршрут для просмотра каталога услуг и добавления в корзину
@router.get("/services", response_class=HTMLResponse)
async def view_services(request: Request, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        # Получаем активные услуги
        async with db.execute("""
            SELECT id, name, description, price, price_per
            FROM services
            WHERE is_active = 1
        """) as cursor:
            services = await cursor.fetchall()
    return templates.TemplateResponse("services.html", {"request": request, "services": services, "user": current_user})

# Маршрут для добавления услуги в корзину
@router.post("/services/add-to-cart")
async def add_to_cart(
    request: Request,
    service_id: int = Form(...),
    quantity: int = Form(...),
    current_user: dict = Depends(role_required(['user']))
):
    if quantity <= 0:
        error_message = "Количество должно быть положительным числом."
        return templates.TemplateResponse("services.html", {"request": request, "error": error_message, "user": current_user})

    # Проверяем, что услуга существует и активна
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT is_active FROM services WHERE id = ?", (service_id,)) as cursor:
            service = await cursor.fetchone()
            if not service or service[0] != 1:
                error_message = "Эта услуга недоступна."
                return templates.TemplateResponse("services.html", {"request": request, "error": error_message, "user": current_user})

    # Получаем текущую корзину из сессии
    cart = request.session.get('cart', [])
    # Добавляем услугу в корзину
    cart.append({'service_id': service_id, 'quantity': quantity})
    request.session['cart'] = cart
    return RedirectResponse(url="/services", status_code=303)

# Маршрут для просмотра корзины
@router.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request, current_user: dict = Depends(get_current_user)):
    cart = request.session.get('cart', [])
    services_in_cart = []
    total_price = 0.0
    async with aiosqlite.connect(DATABASE) as db:
        for item in cart:
            service_id = item['service_id']
            quantity = item['quantity']
            async with db.execute("SELECT id, name, price, price_per FROM services WHERE id = ?", (service_id,)) as cursor:
                service = await cursor.fetchone()
                if service:
                    subtotal = service[2] * quantity
                    total_price += subtotal
                    services_in_cart.append({
                        'service_id': service[0],
                        'name': service[1],
                        'price': service[2],
                        'price_per': service[3],
                        'quantity': quantity,
                        'subtotal': subtotal
                    })
    return templates.TemplateResponse("cart.html", {"request": request, "services_in_cart": services_in_cart, "total_price": total_price, "user": current_user})

# Маршрут для оформления заявки
@router.post("/cart/checkout")
async def checkout(request: Request, current_user: dict = Depends(role_required(['user']))):
    cart = request.session.get('cart', [])
    if not cart:
        error_message = "Ваша корзина пуста."
        return templates.TemplateResponse("cart.html", {"request": request, "services_in_cart": [], "total_price": 0.0, "error": error_message, "user": current_user})
    total_price = 0.0
    services_in_cart = []
    async with aiosqlite.connect(DATABASE) as db:
        # Начинаем транзакцию
        await db.execute("BEGIN")
        try:
            # Создаем новую заявку
            await db.execute("""
                INSERT INTO service_requests (user_id, request_date, status, total_price)
                VALUES (?, datetime('now'), 'Pending', 0)
            """, (current_user['id'],))
            # Получаем ID новой заявки
            async with db.execute("SELECT last_insert_rowid()") as cursor:
                request_id = (await cursor.fetchone())[0]
            # Добавляем услуги в таблицу service_cart_items
            for item in cart:
                service_id = item['service_id']
                quantity = item['quantity']
                async with db.execute("SELECT price FROM services WHERE id = ?", (service_id,)) as cursor:
                    service = await cursor.fetchone()
                    if service:
                        price = service[0]
                        subtotal = price * quantity
                        total_price += subtotal
                        await db.execute("""
                            INSERT INTO service_cart_items (request_id, service_id, quantity)
                            VALUES (?, ?, ?)
                        """, (request_id, service_id, quantity))
            # Обновляем общую стоимость заявки
            await db.execute("""
                UPDATE service_requests
                SET total_price = ?
                WHERE id = ?
            """, (total_price, request_id))
            await db.commit()
            # Очищаем корзину
            request.session['cart'] = []
            return RedirectResponse(url="/service-requests/user", status_code=303)
        except Exception as e:
            await db.execute("ROLLBACK")
            logger.error(f"Ошибка при оформлении заявки: {e}")
            error_message = "Произошла ошибка при оформлении заявки. Пожалуйста, попробуйте позже."
            return templates.TemplateResponse("cart.html", {"request": request, "services_in_cart": services_in_cart, "total_price": total_price, "error": error_message, "user": current_user})

# Маршрут для просмотра собственных заявок пользователем
@router.get("/service-requests/user", response_class=HTMLResponse)
async def user_service_requests(request: Request, current_user: dict = Depends(role_required(['user']))):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("""
            SELECT id, request_date, status, total_price
            FROM service_requests
            WHERE user_id = ?
            ORDER BY request_date DESC
        """, (current_user['id'],)) as cursor:
            requests_list = await cursor.fetchall()
    return templates.TemplateResponse("user_service_requests.html", {"request": request, "requests": requests_list, "user": current_user})

# Маршрут для просмотра деталей заявки пользователя
@router.get("/service-requests/user/{request_id}", response_class=HTMLResponse)
async def user_request_details(request_id: int, request: Request, current_user: dict = Depends(role_required(['user']))):
    async with aiosqlite.connect(DATABASE) as db:
        # Проверяем, что заявка принадлежит текущему пользователю
        async with db.execute("""
            SELECT id, request_date, status, total_price
            FROM service_requests
            WHERE id = ? AND user_id = ?
        """, (request_id, current_user['id'])) as cursor:
            request_info = await cursor.fetchone()
            if not request_info:
                raise HTTPException(status_code=404, detail="Заявка не найдена")
        # Получаем детали услуг в заявке
        async with db.execute("""
            SELECT s.name, s.price, s.price_per, sci.quantity
            FROM service_cart_items sci
            JOIN services s ON sci.service_id = s.id
            WHERE sci.request_id = ?
        """, (request_id,)) as cursor:
            services_in_request = await cursor.fetchall()
    return templates.TemplateResponse("user_request_details.html", {"request": request, "request_info": request_info, "services_in_request": services_in_request, "user": current_user})

# Маршрут для просмотра заявок на услуги (для сотрудников и администраторов)
@router.get("/service-requests", response_class=HTMLResponse)
async def view_service_requests(request: Request, current_user: dict = Depends(role_required(['employee', 'admin']))):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("""
            SELECT sr.id, u.username, sr.request_date, sr.status, sr.total_price
            FROM service_requests sr
            JOIN users u ON sr.user_id = u.id
            ORDER BY sr.request_date DESC
        """) as cursor:
            requests_list = await cursor.fetchall()
    return templates.TemplateResponse("service_requests.html", {"request": request, "requests": requests_list, "user": current_user})

# Маршрут для изменения статуса заявки
@router.post("/service-requests/update-status/{request_id}")
async def update_request_status(
    request_id: int,
    status: str = Form(...),
    current_user: dict = Depends(role_required(['employee', 'admin']))
):
    allowed_statuses = ['Pending', 'In Progress', 'Serviced', 'Rejected']
    if status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Недопустимый статус")
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            UPDATE service_requests
            SET status = ?
            WHERE id = ?
        """, (status, request_id))
        await db.commit()
    return RedirectResponse(url="/service-requests", status_code=303)

# Маршрут для просмотра деталей заявки (для сотрудников и администраторов)
@router.get("/service-requests/{request_id}", response_class=HTMLResponse)
async def request_details(request_id: int, request: Request, current_user: dict = Depends(role_required(['employee', 'admin']))):
    async with aiosqlite.connect(DATABASE) as db:
        # Получаем информацию о заявке
        async with db.execute("""
            SELECT sr.id, u.username, sr.request_date, sr.status, sr.total_price
            FROM service_requests sr
            JOIN users u ON sr.user_id = u.id
            WHERE sr.id = ?
        """, (request_id,)) as cursor:
            request_info = await cursor.fetchone()
            if not request_info:
                raise HTTPException(status_code=404, detail="Заявка не найдена")
        # Получаем детали услуг в заявке
        async with db.execute("""
            SELECT s.name, s.price, s.price_per, sci.quantity
            FROM service_cart_items sci
            JOIN services s ON sci.service_id = s.id
            WHERE sci.request_id = ?
        """, (request_id,)) as cursor:
            services_in_request = await cursor.fetchall()
    return templates.TemplateResponse("request_details.html", {"request": request, "request_info": request_info, "services_in_request": services_in_request, "user": current_user})

# Маршрут для управления услугами
@router.get("/services/manage", response_class=HTMLResponse)
async def manage_services(request: Request, current_user: dict = Depends(role_required(['employee', 'admin']))):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT id, name, description, price, price_per, is_active FROM services") as cursor:
            services = await cursor.fetchall()
    return templates.TemplateResponse("manage_services.html", {"request": request, "services": services, "user": current_user})

# Маршрут для добавления услуги
# Добавление новой услуги
@router.post("/services/add")
async def add_service(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    price_per: str = Form(...),
    category: str = Form(...),  # Категория услуги
    is_active: int = Form(...),
    current_user: dict = Depends(role_required(['employee', 'admin']))
):
    # Если сотрудник добавляет услугу, категория принудительно становится "business"
    if current_user['role'] == 'employee':
        category = 'business'

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            INSERT INTO services (name, description, price, price_per, category, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, description, price, price_per, category, is_active))
        await db.commit()

    return RedirectResponse(url=f"/services/{category}", status_code=303)


# Редактирование услуги
@router.post("/services/edit/{service_id}")
async def edit_service(
    service_id: int,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    price_per: str = Form(...),
    category: str = Form(...),
    is_active: int = Form(...),
    current_user: dict = Depends(role_required(['employee', 'admin']))
):
    # Сотрудники могут редактировать только бизнес-услуги
    if current_user['role'] == 'employee' and category != 'business':
        raise HTTPException(status_code=403, detail="Вы можете редактировать только бизнес-услуги.")
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            UPDATE services
            SET name = ?, description = ?, price = ?, price_per = ?, category = ?, is_active = ?
            WHERE id = ?
        """, (name, description, price, price_per, category, is_active, service_id))
        await db.commit()
    return RedirectResponse(url=f"/services/{category}", status_code=303)


# Маршрут для удаления услуги
@router.post("/services/delete/{service_id}")
async def delete_service(
    request: Request,
    service_id: int,
    current_user: dict = Depends(role_required(['employee', 'admin']))
):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM services WHERE id = ?", (service_id,))
        await db.commit()
    return RedirectResponse(url="/services/manage", status_code=303)

from fastapi import Depends, HTTPException

# Отображение бизнес каталога (доступно клиентам, сотрудникам и администраторам)
@router.get("/services/business", response_class=HTMLResponse)
async def view_business_catalog(request: Request, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("""
            SELECT id, name, description, price, price_per
            FROM services
            WHERE category = 'business' AND is_active = 1
        """) as cursor:
            services = await cursor.fetchall()
    return templates.TemplateResponse("services.html", {"request": request, "services": services, "user": current_user})

# Отображение технического каталога (только для администраторов и сотрудников)
@router.get("/services/technical", response_class=HTMLResponse)
async def view_technical_catalog(request: Request, current_user: dict = Depends(role_required(['employee', 'admin']))):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("""
            SELECT id, name, description, price, price_per
            FROM services
            WHERE category = 'technical' AND is_active = 1
        """) as cursor:
            services = await cursor.fetchall()
    return templates.TemplateResponse("services.html", {"request": request, "services": services, "user": current_user})
