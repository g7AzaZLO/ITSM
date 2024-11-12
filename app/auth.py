import os
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import aiosqlite

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Path to the database file
DATABASE = os.path.join(BASE_DIR, "..", "database", "database.db")

# Function to get the current user
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

@router.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
async def register_post(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    async with aiosqlite.connect(DATABASE) as db:
        # Add the new user with role 'user'
        try:
            await db.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, 'user')",
                (username, email, password)
            )
            await db.commit()
        except aiosqlite.IntegrityError:
            # Username or email already exists
            return templates.TemplateResponse(
                "register.html",
                {"request": request, "error": "Имя пользователя или email уже заняты."}
            )
    return RedirectResponse(url="/login", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
            "SELECT id, password FROM users WHERE username = ?", (username,)
        ) as cursor:
            user = await cursor.fetchone()
            if user and user[1] == password:
                # Set user in session
                request.session['user_id'] = user[0]
                return RedirectResponse(url="/", status_code=303)
    # Invalid credentials
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Неверное имя пользователя или пароль."}
    )

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: dict = Depends(get_current_user)):
    if current_user:
        return templates.TemplateResponse("home.html", {"request": request, "user": current_user})
    else:
        return RedirectResponse(url="/login", status_code=303)
