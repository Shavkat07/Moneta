import uuid
from datetime import datetime
from decimal import Decimal  # <--- ИСПРАВЛЕНО: Стандартный Decimal
from enum import Enum
from typing import Optional, List

from sqlalchemy import Column, DateTime, func, Numeric, UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship
from starlette.requests import Request


class DebtType(str, Enum):
	GIVEN = "given"  # Я дал (мне должны)
	TAKEN = "taken"  # Я взял (я должен)


class DebtStatus(str, Enum):
	ACTIVE = "active"
	PAID = "paid"
	OVERDUE = "overdue"
	FORGIVEN = "forgiven"  # Прощен


# --- МОДЕЛЬ ДОЛЖНИКА (Контакта) ---
class Debtor(SQLModel, table=True):
	__tablename__ = "debtors"
	
	# Уникальность имени/телефона только в рамках одного пользователя
	__table_args__ = (
		UniqueConstraint("user_id", "phone_number", name="unique_user_debtor_phone"),
	)
	
	id: Optional[int] = Field(default=None, primary_key=True)
	
	# Привязываем контакт к пользователю (моя записная книжка)
	user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
	
	name: str = Field(max_length=100)
	phone_number: Optional[str] = Field(default=None, max_length=15)
	
	# Связь с долгами
	debts: List["Debt"] = Relationship(back_populates="debtor")
	
	def __str__(self) -> str:
		phone = f" ({self.phone_number})" if self.phone_number else ""
		return f"{self.name}{phone}"
	
	async def __admin_repr__(self, request: Request):
		return self.__str__()


# --- МОДЕЛЬ ДОЛГА ---
class Debt(SQLModel, table=True):
	__tablename__ = "debts"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	
	# Владелец записи (кто записывает долг)
	user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
	
	# Кто должен / Кому должны
	debtor_id: int = Field(foreign_key="debtors.id")
	debtor: "Debtor" = Relationship(back_populates="debts")
	
	# Валюта (ОБЯЗАТЕЛЬНО)
	currency_id: int = Field(foreign_key="currencies.id")
	currency: "Currency" = Relationship() # Раскомментируй, если нужен доступ к obj.currency
	
	# Сумма (Numeric для точности денег)
	amount: Decimal = Field(sa_column=Column(Numeric(20, 2), nullable=False))
	
	# Сколько уже возвращено (для частичного погашения)
	repaid_amount: Decimal = Field(default=0, sa_column=Column(Numeric(20, 2)))
	
	type: DebtType = Field(index=True, default=DebtType.GIVEN)
	status: DebtStatus = Field(index=True, default=DebtStatus.ACTIVE)
	
	comment: Optional[str] = Field(default=None, max_length=255)
	
	# Дата когда нужно вернуть (может быть пустой, если "как сможешь")
	due_date: Optional[datetime] = Field(
		default=None,
		sa_column=Column(DateTime(timezone=True), nullable=True)
	)
	
	created_at: datetime = Field(
		sa_column=Column(
			DateTime(timezone=True),
			server_default=func.now(),
			nullable=False,
		)
	)
	
	# --- ADMIN REPRESENTATION ---
	
	def __str__(self) -> str:
		# Здесь нельзя обращаться к self.debtor.name синхронно, если не подгружено
		return f"Debt #{self.id} - {self.amount}"
	
	async def __admin_repr__(self, request: Request):
		# В админке можно попробовать получить данные, но лучше показывать ID и Сумму
		direction = "Мне должны" if self.type == DebtType.GIVEN else "Я должен"
		return f"{direction}: {self.amount} (ID: {self.id})"