import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from db.db_config import initialize_collections
from catalog_service.routers import router as catalog_router
from messaging_service.routers import router as messages_router
from users.routers import router as users_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_collections()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(catalog_router, prefix='/catalog', tags=["Catalog"])
app.include_router(messages_router, prefix='/messages', tags=["Chat"])
app.include_router(users_router, prefix='/users', tags=["User"])

@app.get("/")
async def read_root():
    return {"Hello": "World"}

if __name__ == "__main__":
    uvicorn.run(app, port=8006)