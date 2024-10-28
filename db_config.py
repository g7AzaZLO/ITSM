import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Получаем URL и имя базы данных из .env
MONGO_DB_URL = "mongodb://localhost:27017"
MONGO_DB_NAME = "itsm_database"

# Настройка клиента MongoDB
client = AsyncIOMotorClient(MONGO_DB_URL)
database = client[MONGO_DB_NAME]

# Создание коллекций
messages_collection = database["messages"]
services_catalog_collection = database["services_catalog"]
incidents_collection = database["incidents"]


# Проверка подключения
async def check_db_connection() -> None:
    """Проверяет подключение к базе данных."""
    try:
        # Пробный вызов для проверки подключения
        await client.admin.command('ping')
        print("Подключение к MongoDB установлено.")
    except Exception as e:
        print(f"Ошибка подключения к MongoDB: {e}")
