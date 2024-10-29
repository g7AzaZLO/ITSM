from uuid import uuid4
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from messaging_service.models import Message, Chat, SendMessageRequest, CreateChatRequest
from datetime import datetime
from db.db_config import users_collection, messages_collection, chats_collection

router = APIRouter()


def get_current_time():
    return datetime.now()


@router.post("/messages/", response_model=Message)
async def send_message(message: SendMessageRequest):
    # Проверяем существование отправителя и получателя в коллекции пользователей
    sender_exists = await users_collection.find_one({"username": message.sender_username})
    receiver_exists = await users_collection.find_one({"username": message.receiver_username})

    if not sender_exists or not receiver_exists:
        raise HTTPException(status_code=404, detail="User not found")

    # Находим чат по участникам
    chat = await chats_collection.find_one({"participants": sorted([message.sender_username, message.receiver_username])})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    message_id = str(uuid4())
    new_message = {
        "sender_username": message.sender_username,
        "receiver_username": message.receiver_username,
        "content": message.content,
        "timestamp": get_current_time()
    }

    # Добавляем сообщение в чат
    await chats_collection.update_one({"_id": chat["_id"]}, {"$push": {"messages": new_message}})

    return new_message


@router.get("/messages/", response_model=list[Message])
async def get_messages(participant1: str, participant2: str):
    # Сортируем участников для поиска независимо от порядка
    sorted_participants = sorted([participant1, participant2])

    # Находим чат по участникам
    chat = await chats_collection.find_one({"participants": sorted_participants})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Возвращаем все сообщения из найденного чата
    return chat.get("messages", [])  # Возвращаем пустой список, если сообщений нет


@router.post("/chats", response_model=Chat)
async def create_chat(chat: CreateChatRequest):
    if len(chat.participants) != 2:
        raise HTTPException(status_code=400, detail="Chat must have exactly two participants")

    # Сортируем участников, чтобы избежать проблем с порядком
    sorted_participants = sorted(chat.participants)

    # Проверяем наличие существующего чата с теми же участниками
    existing_chat = await chats_collection.find_one({"participants": sorted_participants})
    if existing_chat:
        raise HTTPException(status_code=400, detail="Chat with these participants already exists")

    chat_id = str(uuid4())
    new_chat = Chat(
        id=chat_id,
        participants=sorted_participants,
        messages=[]  # Изначально сообщений нет
    )

    chat_data = new_chat.dict()
    chat_result = await chats_collection.insert_one(chat_data)
    created_chat = await chats_collection.find_one({"_id": chat_result.inserted_id})
    created_chat["_id"] = str(created_chat["_id"])

    return new_chat


@router.get("/chats/", response_model=Chat)
async def get_chat(participant1: str, participant2: str):
    # Сортируем участников для поиска независимо от порядка
    sorted_participants = sorted([participant1, participant2])

    chat = await chats_collection.find_one({"participants": sorted_participants})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat["_id"] = str(chat["_id"])
    return Chat(**chat)
