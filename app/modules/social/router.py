from fastapi import APIRouter
from app.modules.social.routes import (
    debtors,
	debts
)

# Главный роутер модуля Finance
router = APIRouter()

# 1. Подключаем Валюты
router.include_router(
    debtors.router,
    prefix="/debtors",
    tags=["Debtors"]
)

router.include_router(
    debts.router,
    prefix="/debts",
    tags=["Debts"]
)