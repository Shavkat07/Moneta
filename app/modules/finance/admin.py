from sqladmin import ModelView
from app.modules.finance.models import Wallet, Transaction, Category, Currency, CurrencyRate


# --- 1. ВАЛЮТЫ (Currencies) ---
class CurrencyAdmin(ModelView, model=Currency):
	name = "Currency"
	name_plural = "Currencies"
	icon = "fa-solid fa-coins"
	
	column_list = [Currency.char_code, Currency.nominal, Currency.name, Currency.id]
	form_columns = [Currency.code, Currency.char_code, Currency.name, Currency.nominal]


# --- 2. КУРСЫ ВАЛЮТ (Exchange Rates) ---
class CurrencyRateAdmin(ModelView, model=CurrencyRate):
	name = "Exchange Rate"
	name_plural = "Exchange Rates"
	icon = "fa-solid fa-chart-line"
	
	# "currency.char_code" работает, потому что есть связь relationship в модели
	column_list = [CurrencyRate.date, "currency.char_code", CurrencyRate.rate]
	
	# Сортируем по дате (свежие сверху)
	column_default_sort = ("date", True)
	
	form_columns = [CurrencyRate.currency, CurrencyRate.date, CurrencyRate.rate]


# --- 3. КАТЕГОРИИ (Categories) ---
class CategoryAdmin(ModelView, model=Category):
	name = "Category"
	name_plural = "Categories"
	icon = "fa-solid fa-layer-group"
	
	column_list = [Category.name, "parent.name", Category.icon_slug]
	
	# Позволяет выбирать родителя из выпадающего списка
	form_columns = [Category.name, Category.parent, Category.icon_slug]


# --- 4. КОШЕЛЬКИ (Wallets) ---
class WalletAdmin(ModelView, model=Wallet):
	name = "Wallet"
	name_plural = "Wallets"
	icon = "fa-solid fa-wallet"
	
	# Выводим телефон владельца, имя кошелька, баланс и валюту
	column_list = [
		"user.phone_number",
		Wallet.name,
		Wallet.balance,
		"currency_rel.char_code",
		Wallet.type
	]
	
	# Поиск по имени кошелька
	column_searchable_list = [Wallet.name]
	
	# Форма для создания/редактирования
	form_columns = [
		Wallet.user,  # Выпадающий список юзеров (благодаря __str__ в User)
		Wallet.name,
		Wallet.type,
		Wallet.currency_rel,  # Выпадающий список валют
		Wallet.balance
	]


# --- 5. ТРАНЗАКЦИИ (Transactions) ---
class TransactionAdmin(ModelView, model=Transaction):
	name = "Transaction"
	name_plural = "Transactions"
	icon = "fa-solid fa-money-bill-transfer"
	
	column_list = [
		Transaction.id,
		Transaction.amount,
		Transaction.type,
		"wallet.name",  # Имя кошелька
		"category.name",  # Имя категории
		Transaction.created_at
	]
	
	column_default_sort = ("created_at", True)
	
	# Поиск по мерчанту (магазину)
	column_searchable_list = [Transaction.merchant_name]
	
	# # ИСПРАВЛЕНИЕ: Убран Transaction.type из фильтров, так как он вызывает ошибку
	# # Оставляем только те поля, которые sqladmin точно умеет фильтровать (даты, числа, id)
	# column_filters = [
	# 	Transaction.created_at,
	# 	Transaction.amount,
	# 	Transaction.wallet_id
	# ]
	
	form_columns = [
		Transaction.wallet,  # Выбор кошелька
		Transaction.category,  # Выбор категории
		Transaction.amount,
		Transaction.type,  # Здесь (в форме) Enum работает нормально!
		Transaction.merchant_name,
		Transaction.created_at,
		Transaction.is_halal_suspect,
		Transaction.raw_sms_text
	]