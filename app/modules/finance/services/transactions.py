
from fastapi import HTTPException
from sqlmodel import Session

from app.modules.auth.models import User
from app.modules.finance.models import Wallet, TransactionType, Transaction
from app.modules.finance.routes.transactions import _check_sufficient_funds
from app.modules.finance.schemas import TransactionUpdate


def _apply_transaction_balance(wallet: Wallet, amount: float, type: TransactionType, reverse: bool = False):
	"""
	Helper to apply or reverse a transaction's effect on wallet balance.
	If reverse=True, it undoes the operation.
	"""
	# Если reverse=True, то мы "отменяем" действие.
	# Пример: отмена EXPENSE -> balance += amount
	# Пример: отмена INCOME -> balance -= amount
	
	if type == TransactionType.INCOME:
		if reverse:
			_check_sufficient_funds(wallet, amount)
			wallet.balance -= amount
		else:
			wallet.balance += amount
	
	elif type in (TransactionType.EXPENSE, TransactionType.TRANSFER):
		if reverse:
			wallet.balance += amount
		else:
			_check_sufficient_funds(wallet, amount)
			wallet.balance -= amount


def _update_transaction_logic(
		transaction_id: int,
		transaction_in: TransactionUpdate,
		session: Session,
		current_user: User,
		partial: bool = False
):
	# 1. Получаем транзакцию
	transaction = session.get(Transaction, transaction_id)
	if not transaction:
		raise HTTPException(status_code=404, detail="Транзакция не найдена")
	
	# 2. Проверяем доступ к кошельку
	wallet = session.get(Wallet, transaction.wallet_id)
	if not wallet or wallet.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Нет доступа")
	
	# 3. Подготавливаем данные для обновления
	# Используем exclude_unset=True, чтобы не затирать поля значениями None (особенно для PUT с optional полями)
	update_data = transaction_in.model_dump(exclude_unset=True)
	
	# Если ничего не меняется
	if not update_data:
		return transaction
	
	# 4. Проверяем, меняются ли важные поля (amount, type)
	# Если да - нужно пересчитывать баланс
	new_amount = update_data.get("amount", transaction.amount)
	new_type = update_data.get("type", transaction.type)
	
	is_balance_affected = (
			new_amount != transaction.amount or
			new_type != transaction.type
	)
	
	if is_balance_affected:
		# Блокируем кошелек для обновления
		# (в SQLModel/SQLAlchemy лучше делать select with update, но пока упростим)
		session.refresh(wallet)
		
		# А. Откатываем старое значение
		_apply_transaction_balance(wallet, transaction.amount, transaction.type, reverse=True)
		
		# Б. Применяем новое значение
		try:
			_apply_transaction_balance(wallet, new_amount, new_type, reverse=False)
		except HTTPException as e:
			# Если не хватает средств на новую сумму - откатываем всё назад?
			# В данном случае транзакция БД откатится сама при ошибке, если мы не поймаем или если session.commit() упадет.
			# Но `_apply_transaction_balance` кидает HTTPException сразу.
			# Нам нужно, чтобы изменения в wallet.balance не сохранились.
			# Так как мы еще не сделали commit, всё ок.
			raise e
	
	# 5. Обновляем поля транзакции
	for key, value in update_data.items():
		setattr(transaction, key, value)
	
	session.add(wallet)
	session.add(transaction)
	session.commit()
	session.refresh(transaction)
	
	return transaction
