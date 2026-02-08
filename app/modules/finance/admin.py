from sqladmin import ModelView
from app.modules.finance.models import Wallet, Transaction, Category, Currency



class WalletAdmin(ModelView, model=Wallet):
	column_list = [Wallet.id, Wallet.name, Wallet.balance, Wallet.user_id]
	column_details_list = [Wallet.id, Wallet.name, Wallet.balance, Wallet.currency_rel, Wallet.user_id]
	icon = "fa-solid fa-wallet"


class TransactionAdmin(ModelView, model=Transaction):
	column_list = [Transaction.id, Transaction.amount, Transaction.type, Transaction.wallet_id, Transaction.created_at]
	column_sortable_list = [Transaction.created_at, Transaction.amount]
	list_per_page = 20
	icon = "fa-solid fa-money-bill-transfer"


class CategoryAdmin(ModelView, model=Category):
	column_list = [Category.id, Category.name, Category.parent_id]
	icon = "fa-solid fa-layer-group"


class CurrencyAdmin(ModelView, model=Currency):
	column_list = [Currency.char_code, Currency.name, Currency.nominal]
	icon = "fa-solid fa-coins"


