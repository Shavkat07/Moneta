# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.api.router import api_router
from app.core.admin import setup_admin
from app.core.database import create_db_and_tables

# Функция, которая запускается ПЕРЕД стартом приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаем таблицы в БД
    create_db_and_tables()
    print("Startup: Таблицы проверены/созданы.")
    yield
    print("Shutdown: Приложение остановлено.")

app = FastAPI(
    title="Moneta Fintech API",
    version="0.1.0",
    lifespan=lifespan
)

# Подключаем роутеры
app.include_router(api_router, prefix='/api/v1')

setup_admin(app)