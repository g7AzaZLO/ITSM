import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DB_URL = "mongodb://localhost:27017"
MONGO_DB_NAME = "itsm_database"

# Настройка клиента MongoDB
client = AsyncIOMotorClient(MONGO_DB_URL)
database = client[MONGO_DB_NAME]

# Создание коллекций
messages_collection = database["messages"]
services_catalog_collection = database["services_catalog"]
incidents_collection = database["incidents"]
users_collection = database["users"]
chats_collection = database["chats"]
service_orders_collection = database["service_orders"]


# Проверка подключения
async def initialize_collections():
    """Проверяет и создаёт коллекции, если они не существуют."""
    try:
        # Проверяем подключение
        await client.admin.command('ping')
        print("Начало поделючения к MongoDB.")

        # Проверяем и инициализируем коллекции
        collections = await database.list_collection_names()

        if "messages" not in collections:
            await messages_collection.insert_one({"_init": True})
            await messages_collection.delete_many({"_init": True})
            print("Коллекция 'messages' создана.")

        if "services_catalog" not in collections:
            await services_catalog_collection.insert_one({"_init": True})
            await services_catalog_collection.delete_many({"_init": True})
            print("Коллекция 'services_catalog' создана.")

        if "incidents" not in collections:
            await incidents_collection.insert_one({"_init": True})
            await incidents_collection.delete_many({"_init": True})
            print("Коллекция 'incidents' создана.")

        if "users" not in collections:
            await users_collection.insert_one({"_init": True})
            await users_collection.delete_many({"_init": True})
            print("Коллекция 'users' создана.")

        if "chats" not in collections:
            await chats_collection.insert_one({"_init": True})
            await chats_collection.delete_many({"_init": True})
            print("Коллекция 'chats' создана.")

        if "service_orders" not in collections:
            await service_orders_collection.insert_one({"_init": True})
            await service_orders_collection.delete_many({"_init": True})
            print("Коллекция 'service_orders_collection' создана.")
        print("Подключение установлено.")

    except Exception as e:
        print(f"Ошибка при инициализации коллекций MongoDB: {e}")
