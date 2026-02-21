import uuid
from datetime import datetime, UTC
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import Column, DateTime, func
from sqlmodel import SQLModel, Field, Relationship
from starlette.requests import Request

# Импорт нужен только для проверки типов, чтобы не было круговой зависимости (ImportError)
if TYPE_CHECKING:
	from app.modules.finance.models import Wallet


# --- ENUMS ---
class UserLanguage(str, Enum):
	UZ_LAT = "uz_lat"
	UZ_CYR = "uz_cyr"
	RU = "ru"
	EN = "en"


class UserRole(str, Enum):
	USER = "user"
	ADMIN = "admin"


class UserBase(SQLModel):
	phone_number: str = Field(index=True, unique=True, max_length=15)
	full_name: Optional[str] = Field(default=None, max_length=100)
	language_pref: UserLanguage = Field(default=UserLanguage.UZ_LAT)
	email: Optional[str] = Field(default=None)


class User(UserBase, table=True):
	__tablename__ = "users"
	
	id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
	hashed_password: str
	
	is_active: bool = Field(default=True)
	is_verified: bool = Field(default=False)
	role: UserRole = Field(default=UserRole.USER)
	
	created_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),  # Для Pydantic (Python-код)
		sa_column=Column(
			DateTime(timezone=True),
			server_default=func.now(),  # Для SQL (миграции/БД)
			nullable=False,
		)
	)
	
	updated_at: datetime = Field(
		default_factory=lambda: datetime.now(UTC),  # Для Pydantic
		sa_column=Column(
			DateTime(timezone=True),
			server_default=func.now(),  # Начальное значение в БД
			onupdate=func.now(),  # Авто-обновление в БД
			nullable=False,
		)
	)
	
	wallets: List["Wallet"] = Relationship(back_populates="user")
	categories: List["Category"] = Relationship(back_populates="user")
	def __str__(self) -> str:
		return f"{self.full_name} +{self.phone_number}"
	
	async def __admin_repr__(self, request: Request):
		"""Отображение в таблицах и заголовках"""
		return f"{self.full_name} ({self.phone_number})"
	
	async def __admin_select2_repr__(self, request: Request):
		"""Отображение в выпадающем списке (HTML)"""
		# Можно использовать HTML теги для красоты
		return f"<div><span>{self.full_name}</span> <br><small class='text-muted'>{self.phone_number}</small></div>"