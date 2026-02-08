# app/modules/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session
import uuid

from app.core.config import settings
from app.core.database import get_session
from app.modules.auth.models import User
from app.modules.auth.schemas import TokenPayload

# Указываем FastAPI, где искать токен (в заголовке Authorization: Bearer ...)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
		token: str = Depends(oauth2_scheme),
		session: Session = Depends(get_session)
) -> User:
	"""
	Валидирует токен, декодирует его, ищет пользователя в БД.
	Если что-то не так — кидает 401 ошибку.
	"""
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Не удалось подтвердить учетные данные",
		headers={"WWW-Authenticate": "Bearer"},
	)
	
	try:
		# 1. Декодируем токен с помощью Секретного Ключа
		payload = jwt.decode(
			token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
		)
		user_id: str = payload.get("sub")
		print(payload)
		if user_id is None:
			raise credentials_exception
		
		token_data = TokenPayload(sub=user_id)
	
	except JWTError:
		raise credentials_exception
	
	# 2. Ищем пользователя в базе
	user = session.get(User, uuid.UUID(token_data.sub))
	
	if user is None:
		raise credentials_exception
	
	return user