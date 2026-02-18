from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session, select, desc

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.finance.models import Wallet, Transaction
from app.modules.finance.schemas import TransactionRead, TransactionCreate, TransactionUpdate
from app.modules.finance.services.transaction_service import TransactionService

router = APIRouter()


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED, summary="Добавить операцию")
def create_transaction(
		transaction_in: TransactionCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	service = TransactionService(session)
	return service.create_transaction(transaction_in, current_user.id)


@router.get("/all", response_model=List[TransactionRead], summary="История операций")
def get_transactions(
		wallet_id: Optional[int] = None,
		skip: int = 0,
		limit: int = 20,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# Логика выборки простая, её можно оставить в роутере или вынести в `get_all_transactions` метод сервиса
	query = select(Transaction).join(Wallet).where(Wallet.user_id == current_user.id)
	
	if wallet_id:
		query = query.where(Transaction.wallet_id == wallet_id)
	
	query = query.order_by(desc(Transaction.date), desc(Transaction.created_at))
	query = query.offset(skip).limit(limit)
	
	return session.exec(query).all()


@router.get("/{transaction_id}", response_model=TransactionRead, summary="Детали операции")
def get_transaction(
		transaction_id: int,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	service = TransactionService(session)
	return service.get_transaction_or_404(transaction_id, current_user.id)


@router.put("/{transaction_id}", response_model=TransactionRead, summary="Обновить операцию (полностью)")
def update_transaction_put(
		transaction_id: int,
		transaction_in: TransactionUpdate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	service = TransactionService(session)
	return service.update_transaction(transaction_id, transaction_in, current_user.id)


@router.patch("/{transaction_id}", response_model=TransactionRead, summary="Обновить операцию (частично)")
def update_transaction_patch(
		transaction_id: int,
		transaction_in: TransactionUpdate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	service = TransactionService(session)
	# В Pydantic v2 используем exclude_unset при создании модели или внутри сервиса
	# Сервис уже обрабатывает exclude_unset внутри, передаем как есть
	return service.update_transaction(transaction_id, transaction_in, current_user.id)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить операцию")
def delete_transaction(
		transaction_id: int,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	service = TransactionService(session)
	service.delete_transaction(transaction_id, current_user.id)
	return {"ok": True, "detail": "Transaction deleted and balance reverted"}