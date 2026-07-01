from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import close_connections, init_indexes
from app.router import router



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_indexes()
    yield
    await close_connections()


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
