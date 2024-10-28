from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId


class User(BaseModel):
    username: str
    hashed_password: str
    role: str


class Service(BaseModel):
    service_name: str
    description: str
    status: str
    dependencies: Optional[List[str]] = []


class Incident(BaseModel):
    title: str
    description: str
    created_by: str
    assigned_to: Optional[str] = None
    status: str
    created_at: datetime = Field(default_factory=datetime.now())
    updated_at: Optional[datetime] = None


class Message(BaseModel):
    sender_id: str
    receiver_id: str
    message: str
    sent_at: datetime = Field(default_factory=datetime.now())
