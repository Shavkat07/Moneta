from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from sqlmodel import select, Session
from starlette.requests import Request

from app.core.security import verify_password
from app.core.database import engine
from app.modules.auth.admin import UserAdmin
from app.modules.auth.models import User, UserRole
from app.modules.finance.admin import WalletAdmin, TransactionAdmin, CategoryAdmin, CurrencyAdmin
from app.core.config import settings

# --- 1. Настройка Безопасности (Вход в админку) ---
class AdminAuth(AuthenticationBackend):
	async def login(self, request: Request) -> bool:
		form = await request.form()
		username = form.get("username")  # Это будет номер телефона
		password = form.get("password")
		
		# Открываем сессию только для проверки входа
		with Session(engine) as session:
			# Ищем пользователя по номеру телефона
			statement = select(User).where(User.phone_number == username)
			user = session.exec(statement).first()
			
			# Проверяем: пользователь существует + пароль верный + роль ADMIN
			if user and verify_password(password, user.hashed_password):
				if user.role == UserRole.ADMIN:
					# Сохраняем "токен" в сессии браузера (куки)
					request.session.update({"token": str(user.id)})
					return True
		
		return False
	
	async def logout(self, request: Request) -> bool:
		request.session.clear()
		return True
	
	async def authenticate(self, request: Request) -> bool:
		token = request.session.get("token")
		return token is not None


# Инициализируем класс аутентификации (ключ должен быть секретным!)
authentication_backend = AdminAuth(secret_key=settings.ADMIN_SECRET_KEY)

# --- 3. Главная функция подключения ---
def setup_admin(app):
	admin = Admin(app, engine, authentication_backend=authentication_backend, title="Moneta Admin")
	
	# Добавляем все наши view
	admin.add_view(UserAdmin)
	admin.add_view(WalletAdmin)
	admin.add_view(TransactionAdmin)
	admin.add_view(CategoryAdmin)
	admin.add_view(CurrencyAdmin)
