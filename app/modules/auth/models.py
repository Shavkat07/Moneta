import uuid
from datetime import datetime, UTC
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, func
from sqlmodel import SQLModel, Field


# --- ENUMS ---
class UserLanguage(str, Enum):
	UZ_LAT = "uz_lat"
	UZ_CYR = "uz_cyr"
	RU = "ru"
	EN = "en"


class UserRole(str, Enum):
	USER = "user"
	ADMIN = "admin"


# --- BASE (Родитель) ---
# Поля, общие для всех.
class UserBase(SQLModel):
	phone_number: str = Field(index=True, unique=True, max_length=15)
	full_name: Optional[str] = Field(default=None, max_length=100)
	language_pref: UserLanguage = Field(default=UserLanguage.UZ_LAT)
	email: Optional[str] = Field(default=None)


# --- TABLE (Для Базы Данных) ---
# Добавляем ID, хеш пароля и служебные поля.
class User(UserBase, table=True):
	__tablename__ = "users"
	
	id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
	hashed_password: str
	
	is_active: bool = Field(default=True)
	is_verified: bool = Field(default=False)
	role: UserRole = Field(default=UserRole.USER)
	
	created_at: datetime = Field(
		sa_column=Column(
			DateTime(timezone=True),
			server_default=func.now(),
			nullable=False,
		)
	)
	
	updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )
    )
	def __str__(self) -> str:
		return f"{self.full_name} +{self.phone_number}"
