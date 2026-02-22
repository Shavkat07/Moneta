from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import ConfigDict, model_validator, field_validator

from app.modules.finance.models import WalletType, TransactionType, CategoryType
from sqlmodel import SQLModel, Field

# ==========================================
# Конфиг для корректной сериализации Decimal
# ==========================================
# Decimal → str в JSON, чтобы не терять копейки (float неточен для денег).
# Фронтенд может использовать parseFloat() для графиков или отображать как есть.
_money_model_config = ConfigDict(
    json_encoders={Decimal: lambda v: v.to_eng_string()}
)


# 1. Схема для ПАРСИНГА данных с API ЦБ (сырые данные)
# Поля названы так, как приходят от cbu.uz
class CbuCurrencyItem(SQLModel):
    id: int
    # Используем alias, чтобы мапить ключи JSON (Code) в поля Python (code)
    code: str = Field(alias="Code")  # "840"
    char_code: str = Field(alias="Ccy")  # "USD"
    name_ru: str = Field(alias="CcyNm_RU")  # "Доллар США"
    
    # Принимаем строками, валидатор переделает в числа
    nominal_raw: str = Field(alias="Nominal")
    rate_raw: str = Field(alias="Rate")
    date_raw: str = Field(alias="Date")
    
    @property
    def nominal(self) -> int:
        return int(self.nominal_raw)
    
    @property
    def rate(self) -> Decimal:
        # Заменяем запятую на точку, если вдруг ЦБ сменит формат
        clean_rate = self.rate_raw.replace(",", ".")
        return Decimal(clean_rate)
    
    @property
    def parsed_date(self) -> date:
        from datetime import datetime
        return datetime.strptime(self.date_raw, "%d.%m.%Y").date()
    
    # Pydantic конфиг для игнорирования лишних полей (Diff, CcyNm_UZ и т.д.)
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

# 2. Схема для ОТДАЧИ данных на наш фронтенд
class CurrencyRateResponse(SQLModel):
    currency: str    # USD
    rate: float
    date: date
    
    model_config = ConfigDict(
        json_encoders={Decimal: lambda v: v.to_eng_string()}
    )
    

# --- CATEGORY (Категории) ---
class CategoryBase(SQLModel):
    name: str
    type: CategoryType = CategoryType.EXPENSE
    icon_slug: Optional[str] = None
    parent_id: Optional[int] = None
    
class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    type: Optional[CategoryType] = None
    icon_slug: Optional[str] = None
    parent_id: Optional[int] = None
    
class CategoryRead(CategoryBase):
    id: int
    user_id: Optional[UUID]
    children: List["CategoryRead"] = []




# --- WALLET (Кошельки) ---

class WalletBase(SQLModel):
    name: str
    type: WalletType = WalletType.CASH
    currency_code: str

class WalletCreate(WalletBase):
    # При создании можно сразу задать начальный баланс
    balance: Decimal = Decimal("0.00")
    
    @field_validator("currency_code")
    def upper_case_code(cls, v):
        return v.upper()

class WalletUpdate(SQLModel):
    name: Optional[str] = None
    type: Optional[WalletType] = None
    # Баланс обычно меняется транзакциями, но можно оставить возможность правки
    balance: Optional[Decimal] = None

class WalletRead(WalletBase):
    model_config = _money_model_config

    id: int
    balance: Decimal = Decimal("0.00")
    user_id: UUID

    



# --- TRANSACTION (Транзакции) ---

class TransactionBase(SQLModel):
    amount: Decimal = Decimal("0.00")
    type: TransactionType
    category_id: Optional[int] = None
    description: Optional[str] = None
    raw_sms_text: Optional[str] = None


class TransactionCreate(TransactionBase):
    wallet_id: int
    target_wallet_id: Optional[int] = None  # Нужно только для type="transfer"
    
    @model_validator(mode='after')
    def validate_category_logic(self):
        # 1. Если это расход или доход — требуем категорию
        if self.type in (TransactionType.EXPENSE, TransactionType.INCOME):
            if self.category_id is None:
                raise ValueError("Для дохода или расхода необходимо выбрать категорию")
        
        # 2. Если это перевод — категория не нужна (принудительно ставим None)
        elif self.type == TransactionType.TRANSFER:
            self.category_id = None
        
        return self
    
class TransactionRead(TransactionBase):
    model_config = _money_model_config

    id: int
    wallet_id: int
    created_at: datetime


class TransactionUpdate(SQLModel):
    amount: Optional[Decimal] = None
    type: Optional[TransactionType] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    raw_sms_text: Optional[str] = None
    created_at: Optional[datetime] = None