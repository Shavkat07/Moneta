# app/core/security.py
from datetime import datetime, timedelta, UTC
from typing import Optional
from passlib.context import CryptContext
from jose import jwt
from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
	return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
	return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
	to_encode = data.copy()
	if expires_delta:
		expire = datetime.now(UTC) + expires_delta
	else:
		# Используем settings.ACCESS_TOKEN_EXPIRE_MINUTES, если есть, или дефолт
		expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
	
	to_encode.update({"exp": expire})
	
	# ИСПОЛЬЗУЕМ КЛЮЧИ ИЗ SETTINGS
	encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
	return encoded_jwt