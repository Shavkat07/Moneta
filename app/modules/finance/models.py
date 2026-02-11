import uuid
from datetime import date as date_type, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import Column, Numeric, DateTime, func  # Для точной настройки поля в БД
from sqlmodel import SQLModel, Field, Relationship
from starlette.requests import Request

from app.modules.auth.models import User


class WalletType(str, Enum):
	CASH = "cash"
	CARD = "card"
	BANK_ACCOUNT = "bank_account"
	CRYPTO = "crypto"
	OTHER = "other"


class TransactionType(str, Enum):
	INCOME = "income"
	EXPENSE = "expense"
	TRANSFER = "transfer"  # Полезно, если будет перевод между кошельками


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
	wallets: List["Wallet"] = Relationship(back_populates="currency_rel")
	
	def __str__(self):
		return f"{self.char_code} ({self.name})"
	
	async def __admin_repr__(self, request: Request):
		return f"{self.char_code} ({self.name})"
	
	async def __admin_select2_repr__(self, request: Request):
		return f"<span><strong>{self.char_code}</strong> - {self.name}</span>"

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
	
	def __str__(self):
		return f"{self.date}: {self.rate}"
	
	async def __admin_repr__(self, request: Request):
		return f"{self.date}: {self.rate}"
	
	async def __admin_select2_repr__(self, request: Request):
		return f"<div><strong>{self.rate}</strong> <br><small class='text-muted'>Date: {self.date}</small></div>"

class Category(SQLModel, table=True):
	__tablename__ = "categories"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	name: str = Field(max_length=100)
	icon_slug: Optional[str] = Field(default=None, description="Название иконки для фронта")
	
	# Поле внешнего ключа
	parent_id: Optional[int] = Field(default=None, foreign_key="categories.id")
	
	# 1. Связь "Родитель" (Many-to-One)
	# Именно здесь нужен remote_side, указывающий на ID этой же таблицы
	parent: Optional["Category"] = Relationship(
		back_populates="children",
		sa_relationship_kwargs={"remote_side": "Category.id"}
	)
	
	# 2. Связь "Дети" (One-to-Many)
	# Здесь просто указываем обратную связь
	children: List["Category"] = Relationship(back_populates="parent")
	
	# Связь с транзакциями
	transactions: List["Transaction"] = Relationship(back_populates="category")
	
	def __str__(self):
		return self.name
	
	async def __admin_repr__(self, request: Request):
		return self.name
	
	async def __admin_select2_repr__(self, request: Request):
		icon = f"<i class='{self.icon_slug}'></i> " if self.icon_slug else ""
		return f"<span>{icon}{self.name}</span>"

class Wallet(SQLModel, table=True):
	__tablename__ = "wallets"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	
	# Связь с User (из модуля Auth). Используем UUID
	user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
	
	name: str = Field(max_length=100)
	balance: Decimal = Field(default=0, sa_column=Column(Numeric(20, 2)))
	
	# Связь с валютой
	currency_id: int = Field(foreign_key="currencies.id")
	currency_rel: "Currency" = Relationship(back_populates="wallets")
	
	type: WalletType = Field(default=WalletType.CASH)
	
	# Связи
	transactions: List["Transaction"] = Relationship(back_populates="wallet")
	
	user: Optional[User] = Relationship(back_populates="wallets")
	
	def __str__(self):
		return f"{self.name} ({self.balance})"
	
	async def __admin_repr__(self, request: Request):
		return f"{self.name}"
	
	async def __admin_select2_repr__(self, request: Request):
		return f"<div><strong>{self.name}</strong><br><small>Balance: {self.balance}</small></div>"
	
class Transaction(SQLModel, table=True):
	__tablename__ = "transactions"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	
	wallet_id: int = Field(foreign_key="wallets.id")
	wallet: "Wallet" = Relationship(back_populates="transactions")
	
	amount: Decimal = Field(sa_column=Column(Numeric(20, 2)))
	type: TransactionType = Field(index=True)
	
	category_id: Optional[int] = Field(default=None, foreign_key="categories.id", nullable=True)
	category: Optional["Category"] = Relationship(back_populates="transactions")
	
	merchant_name: Optional[str] = Field(default=None, max_length=150)
	raw_sms_text: Optional[str] = Field(default=None, description="Оригинальный текст СМС")
	
	is_halal_suspect: bool = Field(default=False, description="Флаг подозрительной транзакции (Халяль)")
	
	created_at: datetime = Field(
		default=None,
		sa_column=Column(
			DateTime(timezone=True),
			server_default=func.now(),
			nullable=False,
		)
	)

	# Self-referencing Foreign Key
	related_transaction_id: Optional[int] = Field(default=None, foreign_key="transactions.id")
	related_transaction: Optional["Transaction"] = Relationship(
		sa_relationship_kwargs={"remote_side": "Transaction.id"}
	)
	
	def __str__(self):
		desc = self.merchant_name or self.type.value
		return f"{self.amount} - {desc}"
	
	async def __admin_repr__(self, request: Request):
		# Если есть имя мерчанта - показываем его, иначе тип транзакции
		desc = self.merchant_name if self.merchant_name else self.type.value.capitalize()
		return f"{self.amount} ({desc})"
	
	async def __admin_select2_repr__(self, request: Request):
		# Красим сумму: Зеленый для доходов, Красный для расходов
		color_class = "text-success" if self.type == TransactionType.INCOME else "text-danger"
		
		desc = self.merchant_name if self.merchant_name else self.type.value.capitalize()
		date_str = self.created_at.strftime("%Y-%m-%d %H:%M")
		
		return (
			f"<div>"
			f"<strong class='{color_class}'>{self.amount}</strong> "
			f"<span> - {desc}</span><br>"
			f"<small class='text-muted'>{date_str}</small>"
			f"</div>"
		)