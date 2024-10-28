from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"  # Замените на ваш URL к MongoDB

settings = Settings()

client = AsyncIOMotorClient(settings.mongodb_url)
database = client["itsm_database"]