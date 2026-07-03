import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import close_connections, init_indexes
from app.router import router

def _setup_logging() -> None:
    # uvicorn/root 설정에 의존하지 않도록 "app" 로거에 핸들러를 직접 부착한다.
    # basicConfig는 root에 핸들러가 이미 있으면 무시되어 로그가 안 찍히는 경우가 있다.
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("app").info("startup: initializing indexes")
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
