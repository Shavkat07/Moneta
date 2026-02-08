from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
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
    WalletCreate, WalletRead, WalletUpdate,
    TransactionCreate, TransactionRead
)
from app.modules.finance.services.currency_parser import CurrencyClient

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
	category = Category.from_orm(category_in)
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

@router.post("/transactions", response_model=TransactionRead, status_code=201, summary="Добавить доход/расход")
def create_transaction(
		transaction_in: TransactionCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	"""
	Создает транзакцию и АВТОМАТИЧЕСКИ обновляет баланс кошелька.
	"""
	# 1. Ищем кошелек
	wallet = session.get(Wallet, transaction_in.wallet_id)
	if not wallet:
		raise HTTPException(status_code=404, detail="Кошелек не найден")
	
	# 2. Проверка прав (нельзя тратить с чужого кошелька)
	if wallet.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Это не ваш кошелек")
	
	# 3. Логика обновления баланса
	if transaction_in.type == TransactionType.EXPENSE:
		# Если расход - отнимаем
		# (Опционально: можно добавить проверку, не уходим ли в минус)
		wallet.balance -= transaction_in.amount
	elif transaction_in.type == TransactionType.INCOME:
		# Если доход - прибавляем
		wallet.balance += transaction_in.amount
	
	# 4. Создаем запись транзакции
	transaction = Transaction.from_orm(transaction_in)
	
	# 5. Сохраняем всё (и транзакцию, и обновленный баланс кошелька)
	session.add(transaction)
	session.add(wallet)  # Помечаем кошелек как измененный
	
	session.commit()
	session.refresh(transaction)
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
	
	# 3. Откат баланса (обратная логика)
	if transaction.type == TransactionType.EXPENSE:
		# Если удаляем расход, значит деньги возвращаются
		wallet.balance += transaction.amount
	elif transaction.type == TransactionType.INCOME:
		# Если удаляем доход, значит деньги уходят
		wallet.balance -= transaction.amount
	
	# 4. Удаляем и сохраняем
	session.delete(transaction)
	session.add(wallet)
	session.commit()
	
	return {"ok": True, "detail": "Transaction deleted and balance reverted"}