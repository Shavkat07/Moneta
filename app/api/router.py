# app/api/router.py
from fastapi import APIRouter

# Импортируем роутеры из модулей
from app.modules.auth.router import router as auth_router
from app.modules.finance.router import router as finance_router
from app.modules.analytics.router import router as analytics_router

# Создаем главный роутер
api_router = APIRouter()

# Подключаем модули
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(finance_router, prefix="/finance", tags=["Finance"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])