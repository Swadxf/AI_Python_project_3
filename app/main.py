# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import auth, links
from app.database import create_tables  # импорт функции

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запускается один раз при старте приложения
    await create_tables()  # создаём таблицы
    print("Таблицы созданы или уже существуют")
    yield  # здесь приложение работает
    # Можно добавить cleanup, если нужно

app = FastAPI(
    title="Учебный URL Shortener",
    lifespan=lifespan  # ← вот это ключевое
)

app.include_router(auth.router)
app.include_router(links.router)

@app.get("/")
def root():
    return {"message": "Сервис работает → открой /docs"}