from typing import List

from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from db.db_config import services_catalog_collection, service_orders_collection
from catalog_service.models import ServiceCreate, ServiceUpdate, ServiceInDB, ServiceOrder, MultiServiceOrder

router = APIRouter()


@router.post("/services/", response_model=ServiceInDB, status_code=status.HTTP_200_OK)
async def create_service(service: ServiceCreate):
    """Создание новой услуги в каталоге."""
    # Проверяем, существует ли услуга с таким же названием
    existing_service = await services_catalog_collection.find_one({"service_name": service.service_name})
    if existing_service:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Услуга с таким названием уже существует")

    # Добавляем новую услугу
    service_data = service.dict()
    result = await services_catalog_collection.insert_one(service_data)

    # Находим и возвращаем добавленную услугу
    created_service = await services_catalog_collection.find_one({"_id": result.inserted_id})

    # Преобразуем ObjectId в строку перед возвращением
    created_service["_id"] = str(created_service["_id"])
    return ServiceInDB(**created_service)


@router.get("/services/{service_id}", response_model=ServiceInDB)
async def get_service(service_id: str):
    """Получение услуги по ID."""
    service = await services_catalog_collection.find_one({"_id": ObjectId(service_id)})
    if service is None:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
    return ServiceInDB(**service)


@router.get("/services/name/{service_name}", response_model=ServiceInDB)
async def get_service_by_name(service_name: str):
    """Получение услуги по названию."""
    service = await services_catalog_collection.find_one({"service_name": service_name})
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга с таким названием не найдена")

    service["_id"] = str(service["_id"])  # Преобразуем ObjectId в строку перед возвратом
    return ServiceInDB(**service)


@router.get("/services/", response_model=List[ServiceInDB])
async def get_all_services():
    """Получение всех услуг из каталога."""
    services = []
    async for service in services_catalog_collection.find():
        service["_id"] = str(service["_id"])  # Преобразование ObjectId в строку
        services.append(ServiceInDB(**service))
    return services


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


@router.delete("/services/name/{service_name}", status_code=status.HTTP_200_OK)
async def delete_service_by_name(service_name: str):
    """Удаление услуги по названию."""
    result = await services_catalog_collection.delete_one({"service_name": service_name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга с таким названием не найдена")
    return {"detail": f"Услуга '{service_name}' успешно удалена"}


@router.post("/services/order/single", status_code=status.HTTP_201_CREATED)
async def order_service(order: ServiceOrder):
    """Оформление заказа на услугу."""
    # Проверяем, существует ли услуга
    service = await services_catalog_collection.find_one({"_id": ObjectId(order.service_id)})
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Услуга не найдена")

    # Расчет общей цены
    order.total_price = service["price"] * order.quantity

    # Добавляем заказ в коллекцию
    order_data = order.dict()
    result = await service_orders_collection.insert_one(order_data)

    # Возвращаем подтверждение заказа
    created_order = await service_orders_collection.find_one({"_id": result.inserted_id})
    created_order["_id"] = str(created_order["_id"])  # Преобразование ObjectId в строку
    return {"detail": "Заказ успешно оформлен", "order": created_order}


@router.post("/services/order", status_code=status.HTTP_201_CREATED)
async def order_multiple_services(order: MultiServiceOrder):
    """Оформление заказа на несколько услуг одновременно."""
    print("Полученные данные:", order)  # Отладка
    total_price = 0
    order_details = []

    for item in order.items:
        # Проверяем, существует ли услуга
        service = await services_catalog_collection.find_one({"_id": ObjectId(item.service_id)})
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Услуга с ID {item.service_id} не найдена")

        # Рассчитываем цену для текущей услуги и добавляем к общей стоимости
        item_total = service["price"] * item.quantity
        total_price += item_total

        # Добавляем детализированную информацию по услуге в заказ
        order_details.append({
            "service_id": str(item.service_id),
            "service_name": service["service_name"],
            "quantity": item.quantity,
            "item_total": item_total
        })

    # Сохраняем заказ с общей суммой и детализированной информацией
    order_data = order.dict()
    order_data["total_price"] = total_price
    order_data["order_details"] = order_details

    result = await service_orders_collection.insert_one(order_data)

    # Возвращаем подтверждение заказа с информацией о заказанных услугах
    created_order = await service_orders_collection.find_one({"_id": result.inserted_id})
    created_order["_id"] = str(created_order["_id"])  # Преобразуем ObjectId в строку
    return {"detail": "Заказ успешно оформлен", "order": created_order}


@router.get("/services/{service_id}", response_model=ServiceInDB)
async def get_service(service_id: str):
    """Получение услуги по ID."""
    service = await services_catalog_collection.find_one({"_id": ObjectId(service_id)})
    if service is None:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    return ServiceInDB(**service)
