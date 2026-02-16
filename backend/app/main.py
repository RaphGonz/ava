from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import auth, chat, image, onboarding
from app.db.vector import vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    vector_store.connect()
    yield
    vector_store.close()


app = FastAPI(title="AVA", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(image.router, prefix="/api/v1")
app.include_router(onboarding.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
