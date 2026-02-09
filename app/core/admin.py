
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from starlette_admin.contrib.sqla import Admin as StarletteAdmin

from starlette_admin.i18n import I18nConfig

from app.core.admin_auth import MonetaAuthProvider
from app.core.config import settings
from app.core.database import engine


from app.modules.auth.models import User
from app.modules.finance.models import Currency, CurrencyRate, Category, Wallet, Transaction

from app.modules.auth.admin import UserAdmin
from app.modules.finance.admin import (
    CurrencyAdmin,
    CurrencyRateAdmin,
    CategoryAdmin,
    WalletAdmin,
    TransactionAdmin
)



def create_admin():
	# Создаем экземпляр админки
	admin = StarletteAdmin(
		engine,
		title="Moneta Admin",
		logo_url="https://placehold.co/200x50?text=Moneta",  # Можно добавить лого
		auth_provider=MonetaAuthProvider(),
		
		# Настройка локализации (по умолчанию английский, можно включить русский)
		i18n_config=I18nConfig(default_locale="ru"),
		
		middlewares=[
			Middleware(SessionMiddleware, secret_key=settings.ADMIN_SECRET_KEY)
		]
	)
	
	# --- Регистрация Моделей ---
	
	# Auth
	admin.add_view(UserAdmin(User, icon="fa fa-users"))
	
	# Finance
	admin.add_view(WalletAdmin(Wallet, icon="fa fa-wallet"))
	admin.add_view(TransactionAdmin(Transaction, icon="fa fa-money-bill-transfer"))
	admin.add_view(CategoryAdmin(Category, icon="fa fa-layer-group"))
	
	# Справочники (обычно их группируют в Dropdown, но можно и так)
	admin.add_view(CurrencyAdmin(Currency, icon="fa fa-coins", label="Currencies"))
	admin.add_view(CurrencyRateAdmin(CurrencyRate, icon="fa fa-chart-line", label="Exchange Rates"))
	
	return admin
