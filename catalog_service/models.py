from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId


class ServiceBase(BaseModel):
    """Базовая модель для описания услуги."""
    service_name: str = Field(..., title="Название услуги", max_length=100)
    description: Optional[str] = Field(None, title="Описание услуги", max_length=500)
    status: bool = Field(..., title="Доступность услуги", description="Доступна ли услуга")
    price: float = Field(..., title="Цена услуги", ge=0, description="Цена услуги")


class ServiceCreate(ServiceBase):
    """Модель для создания новой услуги."""
    pass


class ServiceUpdate(BaseModel):
    """Модель для обновления данных услуги."""
    service_name: Optional[str] = Field(None, title="Название услуги", max_length=100)
    description: Optional[str] = Field(None, title="Описание услуги", max_length=500)
    status: Optional[bool] = Field(None, title="Доступность услуги")
    price: Optional[float] = Field(None, title="Цена услуги", ge=0)


class ServiceInDB(ServiceBase):
    """Модель для представления услуги, хранящейся в базе данных."""
    id: str = Field(..., alias="_id")

    class Config:
        # Поддержка использования ObjectId
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
