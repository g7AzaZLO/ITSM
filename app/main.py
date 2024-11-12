import os
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.auth import router as auth_router
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key='your-secret-key', session_cookie='session')

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

app.include_router(auth_router)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
