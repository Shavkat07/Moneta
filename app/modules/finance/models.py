from decimal import Decimal
from typing import Optional, List
from datetime import date as date_type

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Numeric  # Для точной настройки поля в БД


# --- Справочник валют ---
class Currency(SQLModel, table=True):
	__tablename__ = "currencies"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	code: str = Field(index=True, unique=True)  # Цифровой код (840)
	char_code: str = Field(index=True, unique=True)  # Буквенный код (USD)
	name: str  # Название
	nominal: int = Field(default=1)  # Номинал
	
	# Связь с историей курсов
	rates: List["CurrencyRate"] = Relationship(back_populates="currency")


# --- История курсов ---
class CurrencyRate(SQLModel, table=True):
	__tablename__ = "currency_rates"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	currency_id: int = Field(foreign_key="currencies.id")
	
	# ВАЖНО: Используем Decimal и Numeric(20, 4)
	# Это позволяет хранить курсы типа 12750.45 или 0.0045 без потери точности
	rate: Decimal = Field(sa_column=Column(Numeric(20, 4)))
	
	# Дата курса
	date: date_type = Field(index=True)
	
	# Обратная связь
	currency: "Currency" = Relationship(back_populates="rates")