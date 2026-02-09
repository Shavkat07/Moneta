# app/modules/finance/admin.py
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.fields import (
	StringField,
	IntegerField,
	DecimalField,
	DateField,
	DateTimeField,
	EnumField,
	HasOne,
	HasMany,
	BooleanField,
	TextAreaField
)
from app.modules.finance.models import Currency, CurrencyRate, Category, Wallet, Transaction, WalletType, \
	TransactionType


class CurrencyAdmin(ModelView):
	fields = [
		StringField("char_code", label="ISO Code"),  # USD
		StringField("code", label="Num Code"),  # 840
		StringField("name", label="Name"),
		IntegerField("nominal", label="Nominal"),
	]
	searchable_fields = ["char_code", "name"]


class CurrencyRateAdmin(ModelView):
	fields = [
		DateField("date", label="Date"),
		HasOne("currency", label="Currency", identity="currency"),
		DecimalField("rate", label="Rate"),
	]
	sortable_fields = ["date"]
	# Сортировка по умолчанию: новые сверху
	page_size = 20


class CategoryAdmin(ModelView):
	fields = [
		StringField("name", label="Name"),
		StringField("icon_slug", label="Icon Slug"),
		
		# Самоссылающаяся связь (Родительская категория)
		HasOne("parent", label="Parent Category", identity="category"),
		HasMany("children", label="Subcategories", identity="category"),
		
		# Показываем подкатегории (детей)
		HasMany("children", label="Subcategories")
	]
	searchable_fields = ["name"]


class WalletAdmin(ModelView):
	fields = [
		HasOne("user", label="Owner", identity="user"),
		StringField("name", label="Wallet Name"),
		DecimalField("balance", label="Balance"),
		HasOne("currency_rel", label="Currency", identity="currency"),
		EnumField("type", label="Type", enum=WalletType),
	]
	searchable_fields = ["name", "user.phone_number"]
	list_per_page = 20


class TransactionAdmin(ModelView):
	fields = [
		StringField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
		
		DateTimeField("created_at", label="Created At"),
		
		EnumField("type", label="Type", enum=TransactionType),
		DecimalField("amount", label="Amount"),
		
		HasOne("wallet", label="Wallet", identity="wallet"),
		HasOne("category", label="Category", identity="category"),
		
		StringField("merchant_name", label="Merchant"),
		TextAreaField("raw_sms_text", label="SMS Raw Text"),
		BooleanField("is_halal_suspect", label="Halal Check"),
	]
	
	# Мощный фильтр для поиска
	searchable_fields = ["merchant_name", "wallet.name", "amount"]
	sortable_fields = ["created_at", "amount"]
	
	# Запрещаем редактирование ID и Даты создания (обычно это не меняют)
	exclude_fields_from_create = ["created_at"]