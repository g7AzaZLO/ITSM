import aiosqlite
from fastapi import Request, HTTPException, status, Depends
from app.config import DATABASE

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
            # Логирование ошибки
            print(f"Ошибка при получении текущего пользователя: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка сервера")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неавторизован")

def role_required(required_roles):
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user['role'] not in required_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
        return current_user
    return role_checker
