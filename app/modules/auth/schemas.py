import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from sqlmodel import SQLModel

from app.modules.auth.models import UserBase, UserRole, UserLanguage


# --- CREATE (Для регистрации) ---
# Фронт шлет это. Мы требуем сырой пароль.
class UserCreate(UserBase):
	password: str = Field(min_length=8)


# --- READ (Для ответа API) ---
# Мы отдаем это. Скрываем пароль, показываем ID и дату регистрации.
class UserRead(UserBase):
	id: uuid.UUID
	is_verified: bool
	role: UserRole
	created_at: datetime


# --- UPDATE (Для редактирования профиля) ---
# Все поля опциональны (можно сменить только имя, не меняя язык).
class UserUpdate(SQLModel):
	full_name: Optional[str] = None
	email: Optional[str] = None
	language_pref: Optional[UserLanguage] = None


# 1. Схема для токена (то, что мы отдаем фронту после логина)
class Token(BaseModel):
	access_token: str
	token_type: str = "bearer"


# 2. Схема содержимого токена (то, что мы расшифровываем из JWT)
class TokenPayload(BaseModel):
	sub: Optional[str] = None  # В sub обычно кладем ID пользователя


# 3. Схема для входа в систему (Login)
# Мы не используем стандартный OAuth2PasswordRequestForm, потому что у нас телефон, а не username
class LoginRequest(BaseModel):
	phone_number: str = Field(..., description="Формат: 998901234567")
	password: str
	
	# Валидатор: проверяем формат узбекского номера
	@field_validator("phone_number")
	def validate_uz_phone(cls, v):
		# Удаляем плюс и пробелы, если прилетели
		clean_number = v.replace("+", "").replace(" ", "")
		# Регулярка для Узб номеров (998 + 9 цифр)
		if not re.match(r"^998\d{9}$", clean_number):
			raise ValueError("Номер должен быть в формате 998XXXXXXXXX")
		return clean_number


# 4. Схема для верификации СМС (Baraka Logic)
class SMSVerifyRequest(BaseModel):
	phone_number: str
	code: str = Field(..., min_length=4, max_length=6, description="Код из СМС")


# 5. Смена пароля (Логика, не связанная напрямую с таблицей User)
class PasswordChangeRequest(BaseModel):
	current_password: str
	new_password: str = Field(..., min_length=8)
