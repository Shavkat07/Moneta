# app/modules/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.database import get_session  # Твоя функция подключения к БД
from app.core.security import create_access_token
from app.modules.auth.models import UserRole, UserLanguage
from app.modules.auth.schemas import Token, LoginRequest
from app.modules.auth.schemas import UserRead, UserCreate
from app.modules.auth.service import AuthService
from app.modules.finance.models import WalletType, TransactionType
from app.modules.social.models import DebtType, DebtStatus

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


@router.post("/access-token", response_model=Token)
def login_for_access_token(
		form_data: OAuth2PasswordRequestForm = Depends(),
		service: AuthService = Depends(get_auth_service)
):
	"""
	Эндпоинт специально для Swagger UI (и других OAuth2 клиентов).
	Принимает username и password в виде формы (не JSON).
	"""
	# Swagger отправляет поле 'username', но мы знаем, что там лежит номер телефона
	user = service.authenticate(form_data.username, form_data.password)
	
	if not user:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Неверный номер телефона или пароль",
			headers={"WWW-Authenticate": "Bearer"},
		)
	
	access_token = create_access_token(data={"sub": str(user.id)})
	return {"access_token": access_token, "token_type": "bearer"}


@router.get("/reference/constants")
def get_constants():
	return {
		"user_types": [e.value for e in UserRole],
		"user_language_types": [e.value for e in UserLanguage],
		"wallet_types": [e.value for e in WalletType],
		"transaction_types": [e.value for e in TransactionType],
		"debt_types": [e.value for e in DebtType],
		"debt_status_types": [e.value for e in DebtStatus],
	}
