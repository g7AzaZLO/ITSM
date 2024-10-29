# models.py
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Базовая модель пользователя."""
    username: str = Field(..., title="имя пользователя", max_length=30)
    role: int = Field(0, title="роль пользователя")
    password: str = Field(..., title="пароль", max_length=500)


class UserCreate(UserBase):
    """Модель для создания пользователя с обязательным паролем."""
    password: str = Field(..., title="пароль", max_length=500)


class UserUpdate(BaseModel):
    """Модель для обновления данных пользователя."""
    username: str = Field(None, title="имя пользователя", max_length=30)
    password: str = Field(None, title="пароль", max_length=500)
    role: int = Field(None, title="роль пользователя")
