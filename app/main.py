import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import close_connections, init_indexes
from app.router import router

def _setup_logging() -> None:
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        app_logger.addHandler(handler)


_setup_logging()
logging.getLogger("app").info("logging configured")
import py_eureka_client.eureka_client as eureka_client
from contextlib import asynccontextmanager
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("app").info("startup: initializing indexes")
    await init_indexes()
    yield
    # await eureka_client.init_async(
    #     eureka_server=settings.eureka_server,
    #     app_name=settings.app_name,
    #     instance_port=settings.instance_port
    # )
    # yield
    await close_connections()
    # await eureka_client.stop_async()


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
