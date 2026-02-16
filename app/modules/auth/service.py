# app/modules/auth/service.py
from sqlmodel import Session, select
from fastapi import HTTPException
from app.modules.auth.models import User
from app.core.security import get_password_hash, verify_password
from app.modules.auth.schemas import UserCreate


class AuthService:
	def __init__(self, session: Session):
		self.session = session
	
	# ЛОГИКА РЕГИСТРАЦИИ
	def create_user(self, user_in: UserCreate) -> User:
		# 1. Проверяем, занят ли телефон
		query = select(User).where(User.phone_number == user_in.phone_number)
		existing_user = self.session.exec(query).first()
		if existing_user:
			raise HTTPException(
				status_code=400,
				detail="Пользователь с таким номером уже существует"
			)
		
		# 2. Хешируем пароль
		hashed_pw = get_password_hash(user_in.password)
		
		# 3. Создаем объект User (но пароль подменяем на хеш)
		# exclude={"password"} убирает сырой пароль из данных
		db_user = User.model_validate(user_in, update={"hashed_password": hashed_pw})
		
		# 4. Сохраняем
		self.session.add(db_user)
		self.session.commit()
		self.session.refresh(db_user)
		return db_user
	
	# ЛОГИКА ВХОДА
	def authenticate(self, phone: str, password: str) -> User:
		# 1. Ищем юзера
		query = select(User).where(User.phone_number == phone)
		user = self.session.exec(query).first()
		
		# 2. Если нет юзера ИЛИ пароль не подошел
		if not user or not verify_password(password, user.hashed_password):
			return None
		
		return user