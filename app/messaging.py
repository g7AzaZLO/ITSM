import os
import logging
from asyncio import AbstractEventLoopPolicy

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiosqlite
from starlette.responses import JSONResponse

from app.dependencies import get_current_user
from app.config import BASE_DIR, DATABASE

logger = logging.getLogger(__name__)
router = APIRouter()
router1 = APIRouter()

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates"))
templates2 = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates2"))

# Маршрут для отображения списка контактов (пользователей)
@router.get("/messages/contacts", response_class=HTMLResponse)
async def contacts(request: Request, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        # Получаем список пользователей, исключая текущего
        async with db.execute("""
            SELECT id, username FROM users WHERE id != ?
        """, (current_user['id'],)) as cursor:
            users = await cursor.fetchall()
        # Получаем список заблокированных пользователей
        async with db.execute("""
            SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
        """, (current_user['id'],)) as cursor:
            blocked_users = [row[0] for row in await cursor.fetchall()]
    return templates.TemplateResponse("contacts.html", {
        "request": request,
        "users": users,
        "blocked_users": blocked_users,
        "user": current_user
    })

# Маршрут для начала или продолжения переписки с другим пользователем
@router.get("/messages/chat/{other_user_id}", response_class=HTMLResponse)
async def chat(other_user_id: int, request: Request, current_user: dict = Depends(get_current_user)):
    if other_user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="Нельзя писать самому себе.")

    async with aiosqlite.connect(DATABASE) as db:
        # Проверяем, не заблокирован ли текущий пользователь получателем
        async with db.execute("""
            SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?
        """, (other_user_id, current_user['id'])) as cursor:
            is_blocked = await cursor.fetchone()
            if is_blocked:
                error_message = "Вы не можете отправить сообщение этому пользователю."
                return templates.TemplateResponse("chat.html", {
                    "request": request,
                    "messages": [],
                    "other_user": None,
                    "error": error_message,
                    "user": current_user
                })
        # Получаем информацию о другом пользователе
        async with db.execute("SELECT id, username FROM users WHERE id = ?", (other_user_id,)) as cursor:
            other_user = await cursor.fetchone()
            if not other_user:
                raise HTTPException(status_code=404, detail="Пользователь не найден.")
        # Получаем сообщения между пользователями
        async with db.execute("""
            SELECT sender_id, receiver_id, content, timestamp
            FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
        """, (current_user['id'], other_user_id, other_user_id, current_user['id'])) as cursor:
            messages = await cursor.fetchall()
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "messages": messages,
        "other_user": other_user,
        "user": current_user
    })

# Маршрут для отправки сообщения
@router.post("/messages/send/{other_user_id}")
async def send_message(other_user_id: int, request: Request, content: str = Form(...), current_user: dict = Depends(get_current_user)):
    if other_user_id == current_user['id']:
        error_message = "Нельзя отправить сообщение самому себе."
        return RedirectResponse(url=f"/messages/chat/{other_user_id}?error={error_message}", status_code=303)
    async with aiosqlite.connect(DATABASE) as db:
        # Проверяем, не заблокирован ли отправитель получателем
        async with db.execute("""
            SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?
        """, (other_user_id, current_user['id'])) as cursor:
            is_blocked = await cursor.fetchone()
            if is_blocked:
                error_message = "Вы не можете отправить сообщение этому пользователю."
                return RedirectResponse(url=f"/messages/chat/{other_user_id}?error={error_message}", status_code=303)
        # Проверяем, не заблокирован ли получатель отправителем
        async with db.execute("""
            SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?
        """, (current_user['id'], other_user_id)) as cursor:
            is_blocked_by_sender = await cursor.fetchone()
            if is_blocked_by_sender:
                error_message = "Вы заблокировали этого пользователя."
                return RedirectResponse(url=f"/messages/chat/{other_user_id}?error={error_message}", status_code=303)
        # Отправляем сообщение
        await db.execute("""
            INSERT INTO messages (sender_id, receiver_id, content, timestamp, is_read)
            VALUES (?, ?, ?, datetime('now'), 0)
        """, (current_user['id'], other_user_id, content))
        await db.commit()
    return RedirectResponse(url=f"/messages/chat/{other_user_id}", status_code=303)

# Маршрут для блокировки пользователя
@router.post("/messages/block/{other_user_id}")
async def block_user(other_user_id: int, current_user: dict = Depends(get_current_user)):
    if other_user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="Нельзя заблокировать самого себя.")
    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute("""
                INSERT INTO blocked_users (user_id, blocked_user_id)
                VALUES (?, ?)
            """, (current_user['id'], other_user_id))
            await db.commit()
        except aiosqlite.IntegrityError:
            # Пользователь уже заблокирован
            pass
    return RedirectResponse(url="/messages/contacts", status_code=303)

# Маршрут для разблокировки пользователя
@router.post("/messages/unblock/{other_user_id}")
async def unblock_user(other_user_id: int, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            DELETE FROM blocked_users
            WHERE user_id = ? AND blocked_user_id = ?
        """, (current_user['id'], other_user_id))
        await db.commit()
    return RedirectResponse(url="/messages/contacts", status_code=303)

# Маршрут для удаления переписки с другим пользователем
@router.post("/messages/delete-conversation/{other_user_id}")
async def delete_conversation(other_user_id: int, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        # Удаляем сообщения, где текущий пользователь является отправителем или получателем с данным пользователем
        await db.execute("""
            DELETE FROM messages
            WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
        """, (current_user['id'], other_user_id, other_user_id, current_user['id']))
        await db.commit()
    return RedirectResponse(url="/messages/contacts", status_code=303)

@router.get("/messages/get/{other_user_id}", response_class=JSONResponse)
async def get_messages(other_user_id: int, current_user: dict = Depends(get_current_user)):
    if other_user_id == current_user['id']:
        return JSONResponse(content={"error": "Нельзя писать самому себе."}, status_code=400)

    async with aiosqlite.connect(DATABASE) as db:
        # Проверяем, не заблокирован ли текущий пользователь получателем
        async with db.execute("""
            SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?
        """, (other_user_id, current_user['id'])) as cursor:
            is_blocked = await cursor.fetchone()
            if is_blocked:
                return JSONResponse(content={"error": "Вы не можете отправить сообщение этому пользователю."}, status_code=403)
        # Получаем сообщения между пользователями
        async with db.execute("""
            SELECT sender_id, receiver_id, content, timestamp
            FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
        """, (current_user['id'], other_user_id, other_user_id, current_user['id'])) as cursor:
            messages = await cursor.fetchall()
        # Формируем список сообщений
        messages_list = []
        for msg in messages:
            messages_list.append({
                "sender_id": msg[0],
                "receiver_id": msg[1],
                "content": msg[2],
                "timestamp": msg[3]
            })
    return JSONResponse(content={"messages": messages_list})


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------






# Маршрут для отображения списка контактов (пользователей)
@router1.get("/messages/contacts", response_class=HTMLResponse)
async def contacts(request: Request, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        # Получаем список пользователей, исключая текущего
        async with db.execute("""
            SELECT id, username FROM users WHERE id != ?
        """, (current_user['id'],)) as cursor:
            users = await cursor.fetchall()
        # Получаем список заблокированных пользователей
        async with db.execute("""
            SELECT blocked_user_id FROM blocked_users WHERE user_id = ?
        """, (current_user['id'],)) as cursor:
            blocked_users = [row[0] for row in await cursor.fetchall()]
    return templates2.TemplateResponse("contacts.html", {
        "request": request,
        "users": users,
        "blocked_users": blocked_users,
        "user": current_user
    })

# Маршрут для начала или продолжения переписки с другим пользователем
@router1.get("/messages/chat/{other_user_id}", response_class=HTMLResponse)
async def chat(other_user_id: int, request: Request, current_user: dict = Depends(get_current_user)):
    if other_user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="Нельзя писать самому себе.")

    async with aiosqlite.connect(DATABASE) as db:
        # Проверяем, не заблокирован ли текущий пользователь получателем
        async with db.execute("""
            SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?
        """, (other_user_id, current_user['id'])) as cursor:
            is_blocked = await cursor.fetchone()
            if is_blocked:
                error_message = "Вы не можете отправить сообщение этому пользователю."
                return templates2.TemplateResponse("chat.html", {
                    "request": request,
                    "messages": [],
                    "other_user": None,
                    "error": error_message,
                    "user": current_user
                })
        # Получаем информацию о другом пользователе
        async with db.execute("SELECT id, username FROM users WHERE id = ?", (other_user_id,)) as cursor:
            other_user = await cursor.fetchone()
            if not other_user:
                raise HTTPException(status_code=404, detail="Пользователь не найден.")
        # Получаем сообщения между пользователями
        async with db.execute("""
            SELECT sender_id, receiver_id, content, timestamp
            FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
        """, (current_user['id'], other_user_id, other_user_id, current_user['id'])) as cursor:
            messages = await cursor.fetchall()
    return templates2.TemplateResponse("chat.html", {
        "request": request,
        "messages": messages,
        "other_user": other_user,
        "user": current_user
    })

# Маршрут для отправки сообщения
@router1.post("/messages/send/{other_user_id}")
async def send_message(other_user_id: int, request: Request, content: str = Form(...), current_user: dict = Depends(get_current_user)):
    if other_user_id == current_user['id']:
        error_message = "Нельзя отправить сообщение самому себе."
        return RedirectResponse(url=f"/messages/chat/{other_user_id}?error={error_message}", status_code=303)
    async with aiosqlite.connect(DATABASE) as db:
        # Проверяем, не заблокирован ли отправитель получателем
        async with db.execute("""
            SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?
        """, (other_user_id, current_user['id'])) as cursor:
            is_blocked = await cursor.fetchone()
            if is_blocked:
                error_message = "Вы не можете отправить сообщение этому пользователю."
                return RedirectResponse(url=f"/messages/chat/{other_user_id}?error={error_message}", status_code=303)
        # Проверяем, не заблокирован ли получатель отправителем
        async with db.execute("""
            SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?
        """, (current_user['id'], other_user_id)) as cursor:
            is_blocked_by_sender = await cursor.fetchone()
            if is_blocked_by_sender:
                error_message = "Вы заблокировали этого пользователя."
                return RedirectResponse(url=f"/messages/chat/{other_user_id}?error={error_message}", status_code=303)
        # Отправляем сообщение
        await db.execute("""
            INSERT INTO messages (sender_id, receiver_id, content, timestamp, is_read)
            VALUES (?, ?, ?, datetime('now'), 0)
        """, (current_user['id'], other_user_id, content))
        await db.commit()
    return RedirectResponse(url=f"/messages/chat/{other_user_id}", status_code=303)

# Маршрут для блокировки пользователя
@router1.post("/messages/block/{other_user_id}")
async def block_user(other_user_id: int, current_user: dict = Depends(get_current_user)):
    if other_user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="Нельзя заблокировать самого себя.")
    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute("""
                INSERT INTO blocked_users (user_id, blocked_user_id)
                VALUES (?, ?)
            """, (current_user['id'], other_user_id))
            await db.commit()
        except aiosqlite.IntegrityError:
            # Пользователь уже заблокирован
            pass
    return RedirectResponse(url="/messages/contacts", status_code=303)

# Маршрут для разблокировки пользователя
@router1.post("/messages/unblock/{other_user_id}")
async def unblock_user(other_user_id: int, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            DELETE FROM blocked_users
            WHERE user_id = ? AND blocked_user_id = ?
        """, (current_user['id'], other_user_id))
        await db.commit()
    return RedirectResponse(url="/messages/contacts", status_code=303)

# Маршрут для удаления переписки с другим пользователем
@router1.post("/messages/delete-conversation/{other_user_id}")
async def delete_conversation(other_user_id: int, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DATABASE) as db:
        # Удаляем сообщения, где текущий пользователь является отправителем или получателем с данным пользователем
        await db.execute("""
            DELETE FROM messages
            WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
        """, (current_user['id'], other_user_id, other_user_id, current_user['id']))
        await db.commit()
    return RedirectResponse(url="/messages/contacts", status_code=303)

@router1.get("/messages/get/{other_user_id}", response_class=JSONResponse)
async def get_messages(other_user_id: int, current_user: dict = Depends(get_current_user)):
    if other_user_id == current_user['id']:
        return JSONResponse(content={"error": "Нельзя писать самому себе."}, status_code=400)

    async with aiosqlite.connect(DATABASE) as db:
        # Проверяем, не заблокирован ли текущий пользователь получателем
        async with db.execute("""
            SELECT 1 FROM blocked_users WHERE user_id = ? AND blocked_user_id = ?
        """, (other_user_id, current_user['id'])) as cursor:
            is_blocked = await cursor.fetchone()
            if is_blocked:
                return JSONResponse(content={"error": "Вы не можете отправить сообщение этому пользователю."}, status_code=403)
        # Получаем сообщения между пользователями
        async with db.execute("""
            SELECT sender_id, receiver_id, content, timestamp
            FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
        """, (current_user['id'], other_user_id, other_user_id, current_user['id'])) as cursor:
            messages = await cursor.fetchall()
        # Формируем список сообщений
        messages_list = []
        for msg in messages:
            messages_list.append({
                "sender_id": msg[0],
                "receiver_id": msg[1],
                "content": msg[2],
                "timestamp": msg[3]
            })
    return JSONResponse(content={"messages": messages_list})