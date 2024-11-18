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

# Маршрут для просмотра всех пользователей (доступен только администраторам)
@router.get("/admin/users", response_class=HTMLResponse)
async def view_users(request: Request, current_user: dict = Depends(role_required(['admin']))):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT id, username, email, role FROM users") as cursor:
            users = await cursor.fetchall()
    return templates.TemplateResponse("admin_users.html", {"request": request, "users": users, "user": current_user})

# Маршрут для отображения формы создания нового пользователя
@router.get("/admin/users/create", response_class=HTMLResponse)
async def create_user_form(request: Request, current_user: dict = Depends(role_required(['admin']))):
    return templates.TemplateResponse("admin_create_user.html", {"request": request, "user": current_user})

# Маршрут для обработки создания нового пользователя
@router.post("/admin/users/create")
async def create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    current_user: dict = Depends(role_required(['admin']))
):
    allowed_roles = ['user', 'employee', 'admin']
    if role not in allowed_roles:
        error_message = "Недопустимая роль."
        return templates.TemplateResponse("admin_create_user.html", {"request": request, "error": error_message, "user": current_user})

    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute("""
                INSERT INTO users (username, email, password, role)
                VALUES (?, ?, ?, ?)
            """, (username, email, password, role))
            await db.commit()
        return RedirectResponse(url="/admin/users", status_code=303)
    except aiosqlite.IntegrityError:
        error_message = "Пользователь с таким именем или email уже существует."
        return templates.TemplateResponse("admin_create_user.html", {"request": request, "error": error_message, "user": current_user})
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}")
        error_message = "Произошла ошибка при создании пользователя."
        return templates.TemplateResponse("admin_create_user.html", {"request": request, "error": error_message, "user": current_user})

# Маршрут для отображения формы изменения роли пользователя
@router.get("/admin/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(user_id: int, request: Request, current_user: dict = Depends(role_required(['admin']))):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT id, username, email, role FROM users WHERE id = ?", (user_id,)) as cursor:
            user_info = await cursor.fetchone()
            if not user_info:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
    return templates.TemplateResponse("admin_edit_user.html", {"request": request, "user_info": user_info, "user": current_user})

# Маршрут для обработки изменения роли пользователя
@router.post("/admin/users/{user_id}/edit")
async def edit_user(
    user_id: int,
    request: Request,
    role: str = Form(...),
    current_user: dict = Depends(role_required(['admin']))
):
    allowed_roles = ['user', 'employee', 'admin']
    if role not in allowed_roles:
        error_message = "Недопустимая роль."
        return templates.TemplateResponse("admin_edit_user.html", {"request": request, "error": error_message, "user_info": {"id": user_id}, "user": current_user})

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

# Маршрут для удаления пользователя
@router.post("/admin/users/{user_id}/delete")
async def delete_user(user_id: int, current_user: dict = Depends(role_required(['admin']))):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        await db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)
