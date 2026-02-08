# app/modules/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from fastapi.security import OAuth2PasswordBearer

from app.core.database import get_session  # Твоя функция подключения к БД
from app.core.security import create_access_token
from app.modules.auth.models import UserRead, UserCreate
from app.modules.auth.schemas import Token, LoginRequest
from app.modules.auth.service import AuthService

router = APIRouter()


# Вспомогательная функция, чтобы не создавать AuthService в каждой ручке руками
def get_auth_service(session: Session = Depends(get_session)):
	return AuthService(session)


# 1. РЕГИСТРАЦИЯ
@router.post("/register", response_model=UserRead, status_code=201)
def register(
		user_in: UserCreate,
		service: AuthService = Depends(get_auth_service)
):
	"""
	Создает нового пользователя.
	Принимает: phone_number, password (сырой)
	Возвращает: UserRead (без пароля)
	"""
	return service.create_user(user_in)


# 2. ЛОГИН
@router.post("/login", response_model=Token)
def login(
		login_data: LoginRequest,  # Валидация телефона (schema)
		service: AuthService = Depends(get_auth_service)
):
	"""
	Проверяет пароль и выдает JWT токен.
	"""
	user = service.authenticate(login_data.phone_number, login_data.password)
	
	if not user:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Неверный номер телефона или пароль",
			headers={"WWW-Authenticate": "Bearer"},
		)
	
	# Если всё ок — генерируем токен
	access_token = create_access_token(data={"sub": str(user.id)})
	
	return {"access_token": access_token, "token_type": "bearer"}