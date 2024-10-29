from pydantic import BaseModel, Field, validator
from bson import ObjectId
from typing import Optional, List


class ServiceBase(BaseModel):
    service_name: str = Field(..., title="Название услуги", max_length=100)
    description: Optional[str] = Field(None, title="Описание услуги", max_length=500)
    status: bool = Field(..., title="Доступность услуги")
    price: float = Field(..., title="Цена услуги", ge=0)

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    service_name: Optional[str] = Field(None, title="Название услуги", max_length=100)
    description: Optional[str] = Field(None, title="Описание услуги", max_length=500)
    status: Optional[bool] = Field(None, title="Доступность услуги")
    price: Optional[float] = Field(None, title="Цена услуги", ge=0)

class ServiceInDB(BaseModel):
    """Модель для представления услуги, хранящейся в базе данных."""
    id: Optional[str] = Field(None, alias="_id")  # Используем alias для MongoDB ObjectId
    service_name: str
    description: Optional[str]
    status: bool
    price: float

    # Валидатор, преобразующий ObjectId в строку
    @validator("id", pre=True, always=True, check_fields=False)
    def convert_objectid_to_str(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ServiceOrder(BaseModel):
    user_id: str = Field(..., title="ID пользователя")
    service_id: str = Field(..., title="ID услуги")
    quantity: int = Field(1, title="Количество", gt=0)
    total_price: Optional[float] = Field(None, title="Общая цена")

class ServiceOrderItem(BaseModel):
    service_id: str = Field(..., title="ID услуги")
    quantity: int = Field(1, title="Количество", gt=0)

class MultiServiceOrder(BaseModel):
    user_id: str = Field(..., title="ID пользователя")
    items: List[ServiceOrderItem] = Field(..., title="Список услуг для заказа")
    total_price: Optional[float] = Field(None, title="Общая цена заказа")
