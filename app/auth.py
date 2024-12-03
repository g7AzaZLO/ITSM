import os
import logging
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiosqlite

# Настройка логирования
logger = logging.getLogger(__name__)

router = APIRouter()
router1 = APIRouter()
# Получаем директорию текущего файла
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Настройка шаблонов Jinja2
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates2 = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates2"))

# Путь к файлу базы данных
DATABASE = os.path.join(BASE_DIR, "..", "database", "database.db")

# Функция для получения текущего пользователя
async def get_current_user(request: Request):
    user_id = request.session.get('user_id')
    if user_id:
        try:
            async with aiosqlite.connect(DATABASE) as db:
                async with db.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,)) as cursor:
                    user = await cursor.fetchone()
                    if user:
                        return {"id": user[0], "username": user[1], "role": user[2]}
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
    return None

# Маршрут для страницы регистрации (GET)
@router.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Маршрут для обработки регистрации (POST)
@router.post("/register")
async def register_post(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    logger.info(f"Получены данные регистрации: username={username}, email={email}")
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Добавляем нового пользователя с ролью 'user'
            await db.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, 'user')",
                (username, email, password)
            )
            await db.commit()
        return RedirectResponse(url="/login", status_code=303)
    except aiosqlite.IntegrityError as e:
        # Логируем подробное сообщение об ошибке
        logger.error(f"IntegrityError при регистрации: {e}")
        error_message = f"Ошибка базы данных: {e}"
        return templates.TemplateResponse("register.html", {"request": request, "error": error_message})
    except Exception as e:
        logger.error(f"Ошибка при регистрации: {e}")
        error_message = f"Произошла ошибка: {e}"
        return templates.TemplateResponse("register.html", {"request": request, "error": error_message})


# Маршрут для страницы входа (GET)
@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Маршрут для обработки входа (POST)
@router.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute(
                "SELECT id, password, role FROM users WHERE username = ?", (username,)
            ) as cursor:
                user = await cursor.fetchone()
                if user and user[1] == password and user[2] != 'user':
                    # Устанавливаем пользователя в сессии
                    request.session['user_id'] = user[0]
                    return RedirectResponse(url="/", status_code=303)
        # Неверные учетные данные
        error_message = "Неверное имя пользователя или пароль."
        return templates.TemplateResponse("login.html", {"request": request, "error": error_message})
    except Exception as e:
        logger.error(f"Ошибка при входе: {e}")
        error_message = "Произошла ошибка при входе. Пожалуйста, попробуйте позже."
        return templates.TemplateResponse("login.html", {"request": request, "error": error_message})

# Маршрут для выхода из системы
@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# Маршрут для домашней страницы
@router.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: dict = Depends(get_current_user)):
    if current_user:
        return templates.TemplateResponse("home.html", {"request": request, "user": current_user})
    else:
        return RedirectResponse(url="/login", status_code=303)

# Маршрут для домашней страницы
@router1.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: dict = Depends(get_current_user)):
    if current_user:
        return templates2.TemplateResponse("home.html", {"request": request, "user": current_user})
    else:
        return RedirectResponse(url="/login", status_code=303)

# Маршрут для выхода из системы
@router1.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# Маршрут для страницы входа (GET)
@router1.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates2.TemplateResponse("login.html", {"request": request})

# Маршрут для обработки входа (POST)
@router1.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute(
                "SELECT id, password, role FROM users WHERE username = ?", (username,)
            ) as cursor:
                user = await cursor.fetchone()
                if user and user[1] == password and user[2] == 'user':
                    # Устанавливаем пользователя в сессии
                    request.session['user_id'] = user[0]
                    return RedirectResponse(url="/", status_code=303)
        # Неверные учетные данные
        error_message = "Неверное имя пользователя или пароль."
        return templates2.TemplateResponse("login.html", {"request": request, "error": error_message})
    except Exception as e:
        logger.error(f"Ошибка при входе: {e}")
        error_message = "Произошла ошибка при входе. Пожалуйста, попробуйте позже."
        return templates2.TemplateResponse("login.html", {"request": request, "error": error_message})

@router1.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates2.TemplateResponse("register.html", {"request": request})

# Маршрут для обработки регистрации (POST)
@router1.post("/register")
async def register_post(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    logger.info(f"Получены данные регистрации: username={username}, email={email}")
    try:
        async with aiosqlite.connect(DATABASE) as db:
            # Добавляем нового пользователя с ролью 'user'
            await db.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, 'user')",
                (username, email, password)
            )
            await db.commit()
        return RedirectResponse(url="/login", status_code=303)
    except aiosqlite.IntegrityError as e:
        # Логируем подробное сообщение об ошибке
        logger.error(f"IntegrityError при регистрации: {e}")
        error_message = f"Ошибка базы данных: {e}"
        return templates2.TemplateResponse("register.html", {"request": request, "error": error_message})
    except Exception as e:
        logger.error(f"Ошибка при регистрации: {e}")
        error_message = f"Произошла ошибка: {e}"
        return templates2.TemplateResponse("register.html", {"request": request, "error": error_message})
