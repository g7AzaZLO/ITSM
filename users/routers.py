from fastapi import APIRouter, HTTPException, status
from db.db_config import database
from users.models import UserCreate, UserUpdate, UserBase

router = APIRouter()

# Создаем коллекцию пользователей
users_collection = database["users"]


@router.post("/users/", response_model=UserBase, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Создание нового пользователя."""
    # Проверка, существует ли уже пользователь с таким именем
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Пользователь с таким именем уже существует")

    user_data = user.dict()
    result = await users_collection.insert_one(user_data)

    created_user = await users_collection.find_one({"_id": result.inserted_id})
    created_user["_id"] = str(created_user["_id"])  # Преобразование ObjectId в строку
    return UserBase(**created_user)


@router.put("/users/{username}", response_model=UserBase)
async def update_user(username: str, user_update: UserUpdate):
    """Обновление данных пользователя."""
    # Фильтруем поля, чтобы обновлять только переданные
    update_data = {k: v for k, v in user_update.dict().items() if v is not None}

    result = await users_collection.update_one({"username": username}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    updated_user = await users_collection.find_one({"username": username})
    updated_user["_id"] = str(updated_user["_id"])  # Преобразование ObjectId в строку
    return UserBase(**updated_user)

@router.get("/users/users/{username}", response_model=UserBase)
async def get_user(username: str):
    """Получение данных пользователя по имени."""
    user = await users_collection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    user["_id"] = str(user["_id"])  # Преобразование ObjectId в строку
    return UserBase(**user)