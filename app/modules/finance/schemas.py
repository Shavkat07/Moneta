from datetime import date
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