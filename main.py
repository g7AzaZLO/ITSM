from fastapi import FastAPI
from contextlib import asynccontextmanager
from db_config import initialize_collections

@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_collections()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"Hello": "World"}
