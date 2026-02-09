# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from sqlmodel import Session

from app.api.router import api_router
from app.core.admin import create_admin
from app.core.database import create_db_and_tables, engine
from app.core.init_data import init_base_currency


# Функция, которая запускается ПЕРЕД стартом приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создаем таблицы в БД
    create_db_and_tables()
    
    with Session(engine) as session:
        init_base_currency(session)
    
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

admin = create_admin()
admin.mount_to(app)