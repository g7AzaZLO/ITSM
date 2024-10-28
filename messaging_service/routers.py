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
    if message.sender_id not in users_collection or message.receiver_id not in users_collection:
        raise HTTPException(status_code=404, detail="User not found")

    message_id = str(uuid4())
    new_message = Message(
        id=message_id,
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        content=message.content,
        timestamp=get_current_time()
    )
    messages_collection[message_id] = new_message
    return new_message


@router.get("/messages/{message_id}", response_model=Message)
async def get_message(message_id: str):
    message = await messages_collection.find_one({"_id": ObjectId(message_id)})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return Message(**message)


@router.post("/chats/", response_model=Chat)
async def create_chat(chat: CreateChatRequest):
    chat_id = str(uuid4())
    new_chat = Chat(
        id=chat_id,
        participants=chat.participants,
        messages=[]
    )
    # chats_db[chat_id] = new_chat
    return new_chat


@router.get("/chats/{chat_id}", response_model=Chat)
async def get_chat(chat_id: str):
    chat = chats_collection.get(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat
