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
	TextAreaField
)
from app.modules.finance.models import WalletType, TransactionType, CategoryType


class CurrencyAdmin(ModelView):
	fields = [
		IntegerField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
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
	page_size = 20


class CategoryAdmin(ModelView):
	identity = "category"
	fields = [
		StringField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
		StringField("name", label="Name"),
		StringField("icon_slug", label="Icon Slug"),
		EnumField("type", label="Type", enum=CategoryType),
		HasOne("user", label="Owner", identity="user"),
		HasOne("parent", label="Parent Category", identity="category"),
		HasMany("children", label="Subcategories", identity="category"),
	]
	searchable_fields = ["name"]
	sortable_fields = ['user']


class WalletAdmin(ModelView):
	identity = "wallet"
	fields = [
		StringField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
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
		StringField("id", label="ID", read_only=True),
		DateTimeField("created_at", label="Created At", read_only=True),
		DecimalField("amount", label="Amount", read_only=True),
		EnumField("type", label="Type", enum=TransactionType, read_only=True),
		HasOne("wallet", label="Wallet", identity="wallet", read_only=True),
		HasOne("target_wallet", label="Target Wallet", identity="wallet", read_only=True),
		HasOne("category", label="Category", identity="category", read_only=True),
		StringField("description", label="Description", read_only=True),
		TextAreaField("raw_sms_text", label="SMS Raw Text", read_only=True),

	]
	
	# Мощный фильтр для поиска
	searchable_fields = ["wallet.name", "amount"]
	sortable_fields = ["created_at", "amount"]
	
	async def can_create(self, request) -> bool:
		return False
	
	async def can_edit(self, request) -> bool:
		return False
	
	async def can_delete(self, request) -> bool:
		return False
	
	# ---------- Разрешаем только просмотр ----------
	async def can_view_details(self, request) -> bool:
		return True

	
	
