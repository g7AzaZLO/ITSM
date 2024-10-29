from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime


class Message(BaseModel):
    """Модель сообщения."""
    sender_username: str = Field(..., title="Имя отправителя")
    receiver_username: str = Field(..., title="Имя получателя")
    content: str = Field(..., title="Содержание сообщения", max_length=1000)
    timestamp: datetime = Field(..., title="Время отправки")


class Chat(BaseModel):
    """Модель чата."""
    participants: List[str] = Field(..., title="Участники чата")
    messages: List[Message] = Field(..., title="Сообщения в чате")


class SendMessageRequest(BaseModel):
    """Запрос на отправку сообщения."""
    sender_username: str = Field(..., title="Имя отправителя")
    receiver_username: str = Field(..., title="Имя получателя")
    content: str = Field(..., title="Содержание сообщения", max_length=1000)


class CreateChatRequest(BaseModel):
    """Запрос на создание чата."""
    participants: List[str] = Field(..., title="Участники чата")