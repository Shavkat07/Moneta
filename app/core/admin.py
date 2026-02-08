from sqlmodel import Session, select
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminUser, AuthProvider, AdminConfig
from starlette_admin.contrib.sqla import Admin as StarletteAdmin
from starlette_admin.exceptions import LoginFailed

from app.core.config import settings
from app.core.database import engine
from app.core.security import verify_password
from app.modules.auth.models import User, UserRole


class MonetaAuthProvider(AuthProvider):
	async def login(
			self,
			username: str,
			password: str,
			remember_me: bool,
			request: Request,
			response: Response,
	) -> Response:
		with Session(engine) as session:
			# Ищем пользователя (поле username в форме - это наш phone_number)
			statement = select(User).where(User.phone_number == username)
			user = session.exec(statement).first()
			
			# 1. Проверяем существование и пароль
			if not user or not verify_password(password, user.hashed_password):
				raise LoginFailed("Неверный номер телефона или пароль")
			
			# 2. Проверяем роль (доступ только админам)
			if user.role != UserRole.ADMIN:
				raise LoginFailed("У вас нет прав администратора")
			
			# 3. Сохраняем данные в сессию
			# Важно: сессия должна быть инициализирована через Middleware
			request.session.update({
				"user_id": str(user.id),
				"user_phone": user.phone_number,
				"user_name": user.full_name or "Admin"
			})
			
			return response
	
	async def is_authenticated(self, request: Request) -> bool:
		# Проверяем, есть ли ID в сессии
		if request.session.get("user_id"):
			# Восстанавливаем состояние (state), чтобы использовать его в других методах
			request.state.user = {
				"id": request.session.get("user_id"),
				"username": request.session.get("user_phone"),
				"name": request.session.get("user_name")
			}
			return True
		return False
	
	def get_admin_user(self, request: Request) -> AdminUser:
		# Получаем данные из state (которые мы положили в is_authenticated)
		user = getattr(request.state, "user", {})
		return AdminUser(
			username=user.get("name") or user.get("username") or "Admin",
			photo_url=None,  # Можно добавить URL аватара, если есть
		)
	
	def get_admin_config(self, request: Request) -> AdminConfig:
		# Настройка заголовка и логотипа
		user = getattr(request.state, "user", {})
		app_title = f"Moneta Admin ({user.get('name', '')})"
		
		return AdminConfig(
			app_title=app_title,
			logo_url=None,
			login_logo_url=None
		)
	
	async def logout(self, request: Request, response: Response) -> Response:
		# Очищаем сессию при выходе
		request.session.clear()
		return response


def create_admin():
	# Создаем админку с нашим провайдером и Middleware для сессий
	admin = StarletteAdmin(
		engine,
		title="Moneta Admin",
		auth_provider=MonetaAuthProvider(),
		i18n_config={"default_locale": "ru"},
		middlewares=[
			Middleware(SessionMiddleware, secret_key=settings.ADMIN_SECRET_KEY)
		]
	)
	
	return admin