# app/core/security.py
from datetime import datetime, timedelta, UTC
from typing import Optional

import bcrypt
from jose import jwt

from app.core.config import settings


# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
	# Превращаем строку в байты
	pwd_bytes = password.encode('utf-8')
	# Генерируем соль и хешируем
	salt = bcrypt.gensalt()
	hashed = bcrypt.hashpw(pwd_bytes, salt)
	# Возвращаем строку для хранения в БД
	return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
	# bcrypt требует байты для проверки
	password_bytes = plain_password.encode('utf-8')
	hashed_bytes = hashed_password.encode('utf-8')
	return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
	to_encode = data.copy()
	if expires_delta:
		expire = datetime.now(UTC) + expires_delta
	else:
		expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
	
	to_encode.update({"exp": expire})
	
	encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
	return encoded_jwt
