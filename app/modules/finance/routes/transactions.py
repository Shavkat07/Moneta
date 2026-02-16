from datetime import datetime, UTC
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, desc

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.finance.models import Wallet, WalletType, TransactionType, Transaction
from app.modules.finance.schemas import TransactionRead, TransactionCreate
from app.modules.finance.services.currency_service import CurrencyService

# Создаем локальный роутер
router = APIRouter()

# ==========================================
# 4. 💸 TRANSACTIONS (Операции)
# ==========================================


def _check_sufficient_funds(wallet: Wallet, amount) -> None:
	"""Проверяет, что на кошельке достаточно средств.
	Для кредитных карт (CARD) минус разрешён."""
	if wallet.type != WalletType.CARD and wallet.balance < amount:
		raise HTTPException(
			status_code=400,
			detail=f"Недостаточно средств на кошельке '{wallet.name}'. "
			        f"Баланс: {wallet.balance}, требуется: {amount}"
		)

@router.post("/", response_model=TransactionRead, status_code=201, summary="Добавить операцию")
def create_transaction(
		transaction_in: TransactionCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# 1. Блокируем исходный кошелек
	print(f"DEBUG: Locking wallet {transaction_in.wallet_id}...")
	statement = select(Wallet).where(Wallet.id == transaction_in.wallet_id)  # .with_for_update()
	wallet = session.exec(statement).one_or_none()
	print(f"DEBUG: Wallet locked: {wallet}")
	
	if not wallet or wallet.user_id != current_user.id:
		raise HTTPException(status_code=404, detail="Кошелек не найден или нет доступа")
	
	# Инициализируем сервис конвертации
	currency_service = CurrencyService(session)
	income_transaction = None
	
	if transaction_in.type == TransactionType.INCOME:
		wallet.balance += transaction_in.amount
	
	elif transaction_in.type == TransactionType.EXPENSE:
		_check_sufficient_funds(wallet, transaction_in.amount)
		wallet.balance -= transaction_in.amount
	
	elif transaction_in.type == TransactionType.TRANSFER:
		if not transaction_in.target_wallet_id:
			raise HTTPException(status_code=400, detail="Для перевода нужен target_wallet_id")
		
		# Блокируем целевой кошелек
		target_stmt = select(Wallet).where(Wallet.id == transaction_in.target_wallet_id)  # .with_for_update()
		target_wallet = session.exec(target_stmt).one_or_none()
		
		if not target_wallet:
			raise HTTPException(status_code=404, detail="Кошелек получателя не найден")
		
		# --- ЛОГИКА КОНВЕРТАЦИИ ---
		# 1. Снимаем сумму с исходного кошелька (в его валюте)
		_check_sufficient_funds(wallet, transaction_in.amount)
		wallet.balance -= transaction_in.amount
		
		# 2. Считаем, сколько это будет в валюте получателя
		converted_amount = currency_service.convert(
			amount=transaction_in.amount,
			from_currency_id=wallet.currency_id,
			to_currency_id=target_wallet.currency_id
		)
		
		# 3. Добавляем сконвертированную сумму получателю
		target_wallet.balance += converted_amount
		
		# 4. Создаем "зеркальную" транзакцию для получателя
		# В описании указываем курс, если была конвертация
		desc_suffix = ""
		if wallet.currency_id != target_wallet.currency_id:
			desc_suffix = f" (Конвертация: {transaction_in.amount} {wallet.currency_rel.char_code})"
		
		income_transaction = Transaction(
			wallet_id=target_wallet.id,
			amount=converted_amount,  # <-- ВАЖНО: сохраняем уже в валюте кошелька-получателя
			type=TransactionType.INCOME,  # Исправлено: для получателя это доход
			category_id=None,
			merchant_name=f"Перевод от {wallet.name}{desc_suffix}",
			created_at=datetime.now(UTC),
			is_halal_suspect=True,
		)
		session.add(income_transaction)
		session.add(target_wallet)
		session.flush()  # Получаем ID
		
		if not transaction_in.merchant_name:
			transaction_in.merchant_name = f"Перевод на {target_wallet.name}"
	
	transaction_data = transaction_in.model_dump(exclude={"target_wallet_id"})
	if transaction_data.get("category_id") == 0:
		transaction_data['category_id'] = None
		
	transaction = Transaction(**transaction_data)
	if income_transaction:
		transaction.related_transaction_id = income_transaction.id
	
	session.add(transaction)
	session.add(wallet)
	session.commit()
	session.refresh(transaction)
	
	# Update related transaction to link back
	if income_transaction:
		income_transaction.related_transaction_id = transaction.id
		session.add(income_transaction)
		session.commit()
	
	return transaction


@router.get("/all", response_model=List[TransactionRead], summary="История операций")
def get_transactions(
		wallet_id: int = None,  # Опциональный фильтр по кошельку
		skip: int = 0,
		limit: int = 20,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# Базовый запрос: джойним кошельки, чтобы убедиться, что они принадлежат юзеру
	query = select(Transaction).join(Wallet).where(Wallet.user_id == current_user.id)
	
	# Если передали wallet_id, фильтруем конкретный кошелек
	if wallet_id:
		query = query.where(Transaction.wallet_id == wallet_id)
	
	# Сортировка по дате (сначала новые)
	query = query.order_by(desc(Transaction.created_at))
	query = query.offset(skip).limit(limit)
	
	transactions = session.exec(query).all()
	return transactions

from app.modules.finance.schemas import TransactionRead, TransactionCreate, TransactionUpdate

# ... (rest of imports are fine, just ensuring TransactionUpdate is available)

@router.get("/{transaction_id}", response_model=TransactionRead, summary="Детали операции")
def get_transaction(
		transaction_id: int,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	"""Выводит все детали одной транзакции по id."""
	transaction = session.get(Transaction, transaction_id)
	
	if not transaction:
		raise HTTPException(status_code=404, detail="Транзакция не найдена")
	
	wallet = session.get(Wallet, transaction.wallet_id)
	if not wallet or wallet.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Нет доступа")

	return transaction


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


@router.put("/{transaction_id}", response_model=TransactionRead, summary="Обновить операцию (полностью)")
def put_transaction(
		transaction_id: int,
		transaction_in: TransactionUpdate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	return _update_transaction_logic(transaction_id, transaction_in, session, current_user)


@router.patch("/{transaction_id}", response_model=TransactionRead, summary="Обновить операцию (частично)")
def patch_transaction(
		transaction_id: int,
		transaction_in: TransactionUpdate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	return _update_transaction_logic(transaction_id, transaction_in, session, current_user, partial=True)


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

@router.delete("/{transaction_id}", summary="Удалить/Отменить операцию")
def delete_transaction(
		transaction_id: int,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	"""
	Удаляет транзакцию и ОТКАТЫВАЕТ баланс кошелька назад.
	"""
	# 1. Ищем транзакцию
	transaction = session.get(Transaction, transaction_id)
	if not transaction:
		raise HTTPException(status_code=404, detail="Транзакция не найдена")
	
	# 2. Подгружаем кошелек
	wallet = session.get(Wallet, transaction.wallet_id)
	if not wallet or wallet.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Нет доступа")
	
	# 3. Handle Linked Transaction
	if transaction.related_transaction_id:
		related = session.get(Transaction, transaction.related_transaction_id)
		if related:
			# Revert related balance
			related_wallet = session.get(Wallet, related.wallet_id)
			if related_wallet:
				if related.type in [TransactionType.EXPENSE, TransactionType.TRANSFER]:
					related_wallet.balance += related.amount
				elif related.type == TransactionType.INCOME:
					_check_sufficient_funds(related_wallet, related.amount)
					related_wallet.balance -= related.amount
				session.add(related_wallet)
			
			# Break link to avoid FK constraint issues
			related.related_transaction_id = None
			session.add(related)
			session.delete(related)
	
	# Break link on current transaction too
	transaction.related_transaction_id = None
	session.add(transaction)
	session.flush()  # Retrieve/Apply changes
	
	# 4. Откат баланса (обратная логика)
	if transaction.type in [TransactionType.EXPENSE, TransactionType.TRANSFER]:
		# Если удаляем расход или перевод, возвращаем деньги
		wallet.balance += transaction.amount
	elif transaction.type == TransactionType.INCOME:
		# Если удаляем доход, списываем деньги
		_check_sufficient_funds(wallet, transaction.amount)
		wallet.balance -= transaction.amount
	
	# 5. Удаляем и сохраняем
	session.delete(transaction)
	session.add(wallet)
	session.commit()
	
	return {"ok": True, "detail": "Transaction deleted and balance reverted"}
