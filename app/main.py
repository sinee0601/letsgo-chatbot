from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import close_connections, init_indexes
from app.router import router
import py_eureka_client.eureka_client as eureka_client
from contextlib import asynccontextmanager
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_indexes()
    yield
    await eureka_client.init_async(
        eureka_server=settings.eureka_server,
        app_name=settings.app_name,
        instance_port=settings.instance_port
    )
    yield
    await close_connections()
    await eureka_client.stop_async()


app = FastAPI(
    title="LetsGO Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
