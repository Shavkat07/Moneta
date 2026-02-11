from datetime import datetime, UTC
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, desc

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
# Импорт моделей и схем
from app.modules.finance.models import (
	Currency, CurrencyRate,
	Category, Wallet, Transaction,
	TransactionType
)
from app.modules.finance.schemas import (
	CurrencyRateResponse,
	CategoryCreate, CategoryRead,
	WalletCreate, WalletRead, TransactionCreate, TransactionRead
)
from app.modules.finance.services.currency_parser import CurrencyClient
from app.modules.finance.services.currency_service import CurrencyService

router = APIRouter()


# ==========================================
# 1. 💵 CURRENCY (Валюты)
# ==========================================

@router.post("/refresh-currency")
async def refresh_currency_rates(session: Session = Depends(get_session)):
	"""Обновляет курсы с сайта ЦБ"""
	client = CurrencyClient()
	try:
		return await client.update_rates(session)
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest-currency", response_model=List[CurrencyRateResponse])
def get_latest_rates(session: Session = Depends(get_session)):
	"""Берет последние курсы из БД"""
	# Логика: берем последние добавленные курсы.
	# В идеале нужно делать DISTINCT по валюте с сортировкой по дате,
	# но для простоты берем курсы за "сегодня" или просто последние 10 записей
	
	statement = select(CurrencyRate).order_by(CurrencyRate.date.desc()).limit(10)
	rates = session.exec(statement).all()
	
	response = []
	for r in rates:
		# Важно: r.currency подгрузится лениво (lazy), так как в модели Relationship
		response.append(CurrencyRateResponse(
			currency=r.currency.char_code,
			rate=r.rate,
			date=r.date
		))
	return response


# ==========================================
# 2. 🗂 CATEGORIES (Категории)
# ==========================================

@router.post("/categories", response_model=CategoryRead, summary="Создать категорию")
def create_category(
		category_in: CategoryCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)  # Требуем авторизацию
):
	# Можно добавить проверку: только админ может создавать глобальные категории
	category = Category.model_validate(category_in)
	session.add(category)
	session.commit()
	session.refresh(category)
	return category


@router.get("/categories", response_model=List[CategoryRead], summary="Список всех категорий")
def get_categories(
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# Получаем корневые категории (у которых нет родителя),
	# Pydantic схема сама подтянет детей (children), если они загружены
	# Для простоты пока отдаем плоский список или все сразу
	categories = session.exec(select(Category)).all()
	return categories


# ==========================================
# 3. 👛 WALLETS (Кошельки)
# ==========================================

@router.post("/wallets", response_model=WalletRead, status_code=201, summary="Создать кошелек")
def create_wallet(
		wallet_in: WalletCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# 1. Проверяем валюту
	currency = session.get(Currency, wallet_in.currency_id)
	if not currency:
		raise HTTPException(status_code=404, detail="Валюта не найдена")
	
	# 2. Создаем кошелек, привязываем к юзеру
	wallet = Wallet(
		**wallet_in.model_dump(),
		user_id=current_user.id
	)
	
	session.add(wallet)
	session.commit()
	session.refresh(wallet)
	return wallet


@router.get("/wallets", response_model=List[WalletRead], summary="Мои кошельки")
def get_my_wallets(
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# Показываем только кошельки текущего пользователя
	statement = select(Wallet).where(Wallet.user_id == current_user.id)
	wallets = session.exec(statement).all()
	return wallets


@router.get("/wallets/{wallet_id}", response_model=WalletRead)
def get_wallet_detail(
		wallet_id: int,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	wallet = session.get(Wallet, wallet_id)
	if not wallet or wallet.user_id != current_user.id:
		raise HTTPException(status_code=404, detail="Кошелек не найден")
	return wallet


# ==========================================
# 4. 💸 TRANSACTIONS (Операции)
# ==========================================

@router.post("/transactions", response_model=TransactionRead, status_code=201, summary="Добавить операцию")
def create_transaction(
		transaction_in: TransactionCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# 1. Блокируем исходный кошелек
	print(f"DEBUG: Locking wallet {transaction_in.wallet_id}...")
	statement = select(Wallet).where(Wallet.id == transaction_in.wallet_id)#.with_for_update()
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
		wallet.balance -= transaction_in.amount
	
	elif transaction_in.type == TransactionType.TRANSFER:
		if not transaction_in.target_wallet_id:
			raise HTTPException(status_code=400, detail="Для перевода нужен target_wallet_id")
		
		# Блокируем целевой кошелек
		target_stmt = select(Wallet).where(Wallet.id == transaction_in.target_wallet_id)#.with_for_update()
		target_wallet = session.exec(target_stmt).one_or_none()
		
		if not target_wallet:
			raise HTTPException(status_code=404, detail="Кошелек получателя не найден")
		
		# --- ЛОГИКА КОНВЕРТАЦИИ ---
		# 1. Снимаем сумму с исходного кошелька (в его валюте)
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
			type=TransactionType.INCOME, # Исправлено: для получателя это доход
			category_id=None,
			merchant_name=f"Перевод от {wallet.name}{desc_suffix}",
			created_at=datetime.now(UTC),
			is_halal_suspect=True,
		)
		session.add(income_transaction)
		session.add(target_wallet)
		session.flush() # Получаем ID

		if not transaction_in.merchant_name:
			transaction_in.merchant_name = f"Перевод на {target_wallet.name}"

	transaction_data = transaction_in.model_dump(exclude={"target_wallet_id"})
	
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

@router.get("/transactions", response_model=List[TransactionRead], summary="История операций")
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


@router.delete("/transactions/{transaction_id}", summary="Удалить/Отменить операцию")
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
					related_wallet.balance -= related.amount
				session.add(related_wallet)
			
			# Break link to avoid FK constraint issues
			related.related_transaction_id = None
			session.add(related)
			session.delete(related)
	
	# Break link on current transaction too
	transaction.related_transaction_id = None
	session.add(transaction)
	session.flush() # Retrieve/Apply changes

	# 4. Откат баланса (обратная логика)
	if transaction.type in [TransactionType.EXPENSE, TransactionType.TRANSFER]:
		# Если удаляем расход или перевод, возвращаем деньги
		wallet.balance += transaction.amount
	elif transaction.type == TransactionType.INCOME:
		# Если удаляем доход, списываем деньги
		wallet.balance -= transaction.amount
	
	# 5. Удаляем и сохраняем
	session.delete(transaction)
	session.add(wallet)
	session.commit()
	
	return {"ok": True, "detail": "Transaction deleted and balance reverted"}
