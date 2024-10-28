from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from db_config import services_catalog_collection
from catalog_service.models import ServiceCreate, ServiceUpdate, ServiceInDB

router = APIRouter()


@router.post("/services/", response_model=ServiceInDB)
async def create_service(service: ServiceCreate, status_code=status.HTTP_200_OK):
    """Создание новой услуги в каталоге."""
    # Проверяем, существует ли услуга с таким же названием
    existing_service = await services_catalog_collection.find_one({"service_name": service.service_name})
    if existing_service:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Услуга с таким названием уже существует")

    service_data = service.dict()
    result = await services_catalog_collection.insert_one(service_data)

    created_service = await services_catalog_collection.find_one({"_id": result.inserted_id})
    return ServiceInDB(**created_service)


@router.get("/services/{service_id}", response_model=ServiceInDB)
async def get_service(service_id: str):
    """Получение услуги по ID."""
    service = await services_catalog_collection.find_one({"_id": ObjectId(service_id)})
    if service is None:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    return ServiceInDB(**service)


@router.put("/services/{service_id}", response_model=ServiceInDB)
async def update_service(service_id: str, service_update: ServiceUpdate):
    """Обновление информации об услуге."""
    update_data = {k: v for k, v in service_update.dict().items() if v is not None}
    result = await services_catalog_collection.update_one(
        {"_id": ObjectId(service_id)}, {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Услуга не найдена или данные не изменены")
    updated_service = await services_catalog_collection.find_one({"_id": ObjectId(service_id)})
    return ServiceInDB(**updated_service)


@router.delete("/services/{service_id}")
async def delete_service(service_id: str):
    """Удаление услуги по ID."""
    result = await services_catalog_collection.delete_one({"_id": ObjectId(service_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    return {"detail": "Услуга успешно удалена"}
