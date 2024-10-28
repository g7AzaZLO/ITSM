from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime


class User(BaseModel):
    """Модель пользователя."""
    # id: str = Field(..., title="ID пользователя")
    username: str = Field(..., title="Имя пользователя", max_length=50)
    email: EmailStr = Field(..., title="Email пользователя")
    created_at: datetime = Field(..., title="Дата создания")


class Message(BaseModel):
    """Модель сообщения."""
    # id: str = Field(..., title="ID сообщения")
    sender_id: str = Field(..., title="ID отправителя")
    receiver_id: str = Field(..., title="ID получателя")
    content: str = Field(..., title="Содержание сообщения", max_length=1000)
    timestamp: datetime = Field(..., title="Время отправки")


class Chat(BaseModel):
    """Модель чата."""
    # id: str = Field(..., title="ID чата")
    participants: List[str] = Field(..., title="Участники чата")
    messages: List[Message] = Field(..., title="Сообщения в чате")


class CreateUserRequest(BaseModel):
    """Запрос на создание пользователя."""
    username: str = Field(..., title="Имя пользователя", max_length=50)
    email: EmailStr = Field(..., title="Email пользователя")
    password: str = Field(..., title="Пароль пользователя", min_length=8)


class SendMessageRequest(BaseModel):
    """Запрос на отправку сообщения."""
    sender_id: str = Field(..., title="ID отправителя")
    receiver_id: str = Field(..., title="ID получателя")
    content: str = Field(..., title="Содержание сообщения", max_length=1000)


class CreateChatRequest(BaseModel):
    """Запрос на создание чата."""
    participants: List[str] = Field(..., title="Участники чата")