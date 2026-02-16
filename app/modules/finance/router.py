from fastapi import APIRouter
from app.modules.finance.routes import (
    currencies,
    categories,
    wallets,
    transactions
)

# Главный роутер модуля Finance
router = APIRouter()

# 1. Подключаем Валюты
router.include_router(
    currencies.router,
    prefix="/currency",     # Итоговый путь: /api/v1/finance/currency/...
    tags=["Currencies"]     # <--- ВОТ ЧТО ДЕЛИТ ИХ В SWAGGER
)

# 2. Подключаем Категории
router.include_router(
    categories.router,
    prefix="/categories",
    tags=["Categories"]
)

# 3. Подключаем Кошельки
router.include_router(
    wallets.router,
    prefix="/wallets",
    tags=["Wallets"]
)

# 4. Подключаем Транзакции
router.include_router(
    transactions.router,
    prefix="/transactions",
    tags=["Transactions"]
)


