# Логика JWT и хеширования
# app/core/security.py
from datetime import datetime, timedelta, UTC
from typing import Optional
from passlib.context import CryptContext
from jose import jwt

# Настройки (в реальном проекте бери из env!)
SECRET_KEY = "super-secret-key-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 1. Хеширование (превращаем "123456" в "$2b$12$EixZa...")
def get_password_hash(password: str) -> str:
	return pwd_context.hash(password)


# 2. Проверка (сравниваем введенный пароль с хешем из БД)
def verify_password(plain_password: str, hashed_password: str) -> bool:
	return pwd_context.verify(plain_password, hashed_password)


# 3. Создание Токена (выдаем "пропуск")
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
	to_encode = data.copy()
	if expires_delta:
		expire = datetime.now(UTC) + expires_delta
	else:
		expire = datetime.now(UTC) + timedelta(minutes=15)
	
	to_encode.update({"exp": expire})
	encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
	return encoded_jwt