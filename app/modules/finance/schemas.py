from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from app.modules.finance.models import WalletType, TransactionType
from sqlmodel import SQLModel


# 1. Схема для ПАРСИНГА данных с API ЦБ (сырые данные)
# Поля названы так, как приходят от cbu.uz
class CurrencySchema(SQLModel):
    id: int
    Code: str        # "840"
    Ccy: str         # "USD"
    CcyNm_RU: str    # "Доллар США"
    Nominal: str     # "1" (строкой приходит)
    Rate: str        # "12047.45" (строкой приходит)
    Date: str        # "12.12.2025"

# 2. Схема для ОТДАЧИ данных на наш фронтенд
class CurrencyRateResponse(SQLModel):
    currency: str    # USD
    rate: float
    date: date
    


# --- CATEGORY (Категории) ---
class CategoryBase(SQLModel):
    name: str
    icon_slug: Optional[str] = None
    parent_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: int
    children: List["CategoryRead"] = []
    # Можно добавить поле children, если будем строить дерево
    


# --- WALLET (Кошельки) ---

class WalletBase(SQLModel):
    name: str
    type: WalletType = WalletType.CASH
    currency_id: int

class WalletCreate(WalletBase):
    # При создании можно сразу задать начальный баланс
    balance: Decimal = Decimal("0.00")

class WalletUpdate(SQLModel):
    name: Optional[str] = None
    type: Optional[WalletType] = None
    # Баланс обычно меняется транзакциями, но можно оставить возможность правки
    balance: Optional[Decimal] = None

class WalletRead(WalletBase):
    id: int
    balance: Decimal
    user_id: UUID
    # Можно добавить поле currency_code, чтобы фронту не искать по ID
    currency: Optional[str] = None
    


# --- TRANSACTION (Транзакции) ---

class TransactionBase(SQLModel):
    amount: Decimal
    type: TransactionType
    category_id: Optional[int] = None
    merchant_name: Optional[str] = None
    raw_sms_text: Optional[str] = None
    is_halal_suspect: bool = False

class TransactionCreate(TransactionBase):
    wallet_id: int
    # Дата может быть передана (если это импорт истории) или пропущена (тогда текущая)
    created_at: Optional[datetime] = None

class TransactionRead(TransactionBase):
    id: int
    wallet_id: int
    created_at: datetime