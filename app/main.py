import os
import logging
from fastapi import FastAPI, Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from app.auth import router as auth_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем директорию текущего файла
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Инициализация приложения FastAPI
app = FastAPI()

# Настройка сессий
app.add_middleware(SessionMiddleware, secret_key='your-secret-key', session_cookie='session')

# Подключение статических файлов
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Подключение маршрутов из файла auth.py
app.include_router(auth_router)

# Настройка шаблонов Jinja2
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Маршрут для главной страницы
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Проверяем, есть ли текущий пользователь
    user = request.session.get('user_id')
    if user:
        # Если пользователь авторизован, отображаем домашнюю страницу
        return templates.TemplateResponse("home.html", {"request": request})
    else:
        # Если нет, перенаправляем на страницу входа
        return RedirectResponse(url="/login", status_code=303)

# Маршрут для тестирования
@app.get("/test")
async def test():
    return {"message": "Test successful"}

# Middleware для логирования запросов (опционально)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Получен запрос: {request.method} {request.url}")
    response = await call_next(request)
    return response
