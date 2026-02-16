from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, desc

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.finance.models import Currency

from app.modules.social.models import Debtor, Debt, DebtStatus, DebtType
from app.modules.social.schemas import (
	DebtorCreate, DebtorRead, DebtorUpdate,
	DebtCreate, DebtRead, DebtUpdate
)

router = APIRouter()


# ==========================================
# 1. 👥 DEBTORS (Контакты / Должники)
# ==========================================

@router.post("/debtors", response_model=DebtorRead, status_code=201, summary="Создать контакт")
def create_debtor(
		debtor_in: DebtorCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	"""
	Создает нового человека в вашей долговой книге.
	Имя и телефон должны быть уникальны для вашего аккаунта.
	"""
	# Проверка на дубликат (по телефону, если он указан)
	if debtor_in.phone_number:
		existing = session.exec(
			select(Debtor)
			.where(Debtor.user_id == current_user.id)
			.where(Debtor.phone_number == debtor_in.phone_number)
		).first()
		if existing:
			raise HTTPException(status_code=400, detail="Контакт с таким номером уже существует")
	
	debtor = Debtor.model_validate(debtor_in)
	debtor.user_id = current_user.id
	
	session.add(debtor)
	session.commit()
	session.refresh(debtor)
	return debtor


@router.get("/debtors", response_model=List[DebtorRead], summary="Список контактов")
def get_debtors(
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	"""Возвращает всех людей, с которыми у вас есть финансовые отношения."""
	statement = select(Debtor).where(Debtor.user_id == current_user.id)
	debtors = session.exec(statement).all()
	return debtors


@router.patch("/debtors/{debtor_id}", response_model=DebtorRead, summary="Обновить контакт")
def update_debtor(
		debtor_id: int,
		debtor_in: DebtorUpdate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	debtor = session.get(Debtor, debtor_id)
	if not debtor or debtor.user_id != current_user.id:
		raise HTTPException(status_code=404, detail="Контакт не найден")
	
	debtor_data = debtor_in.model_dump(exclude_unset=True)
	for key, value in debtor_data.items():
		setattr(debtor, key, value)
	
	session.add(debtor)
	session.commit()
	session.refresh(debtor)
	return debtor


# ==========================================
# 2. 📒 DEBTS (Долги)
# ==========================================

@router.post("/debts", response_model=DebtRead, status_code=201, summary="Записать долг")
def create_debt(
		debt_in: DebtCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# 1. Проверяем, существует ли должник и принадлежит ли он пользователю
	debtor = session.get(Debtor, debt_in.debtor_id)
	if not debtor or debtor.user_id != current_user.id:
		raise HTTPException(status_code=404, detail="Должник не найден в вашем списке")
	
	# 2. Проверяем валюту
	currency = session.get(Currency, debt_in.currency_id)
	if not currency:
		raise HTTPException(status_code=404, detail="Валюта не найдена")
	
	# 3. Создаем запись
	debt = Debt.model_validate(debt_in)
	debt.user_id = current_user.id
	debt.repaid_amount = 0  # Новый долг всегда с 0 погашением
	
	session.add(debt)
	session.commit()
	session.refresh(debt)
	return debt


@router.get("/debts", response_model=List[DebtRead], summary="Список долгов")
def get_debts(
		debtor_id: Optional[int] = None,
		status: Optional[DebtStatus] = None,
		type: Optional[DebtType] = None,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	"""
	Получить список долгов с фильтрацией.
	- **debtor_id**: фильтр по конкретному человеку
	- **status**: active, paid, overdue
	- **type**: given (мне должны), taken (я должен)
	"""
	query = select(Debt).where(Debt.user_id == current_user.id)
	
	if debtor_id:
		query = query.where(Debt.debtor_id == debtor_id)
	if status:
		query = query.where(Debt.status == status)
	if type:
		query = query.where(Debt.type == type)
	
	# Сортируем: сначала активные, потом по дате создания (новые сверху)
	query = query.order_by(Debt.status, desc(Debt.created_at))
	
	debts = session.exec(query).all()
	return debts


@router.get("/debts/{debt_id}", response_model=DebtRead)
def get_debt_detail(
		debt_id: int,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	debt = session.get(Debt, debt_id)
	if not debt or debt.user_id != current_user.id:
		raise HTTPException(status_code=404, detail="Запись о долге не найдена")
	return debt


@router.patch("/debts/{debt_id}", response_model=DebtRead, summary="Обновить долг / Погасить часть")
def update_debt(
		debt_id: int,
		debt_in: DebtUpdate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	"""
	Используйте этот метод для частичного погашения или изменения статуса.
	Если repaid_amount >= amount, статус автоматически станет PAID.
	"""
	debt = session.get(Debt, debt_id)
	if not debt or debt.user_id != current_user.id:
		raise HTTPException(status_code=404, detail="Запись о долге не найдена")
	
	update_data = debt_in.model_dump(exclude_unset=True)
	
	for key, value in update_data.items():
		setattr(debt, key, value)
	
	# --- АВТОМАТИКА ---
	# Если долг полностью погашен, меняем статус на PAID
	if debt.repaid_amount >= debt.amount and debt.status != DebtStatus.PAID:
		debt.status = DebtStatus.PAID
	
	# Если статус вручную сменили на PAID, но сумму не подтянули -> подтягиваем
	if debt.status == DebtStatus.PAID and debt.repaid_amount < debt.amount:
		debt.repaid_amount = debt.amount
	
	session.add(debt)
	session.commit()
	session.refresh(debt)
	return debt


@router.delete("/debts/{debt_id}", status_code=204, summary="Удалить запись")
def delete_debt(
		debt_id: int,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	debt = session.get(Debt, debt_id)
	if not debt or debt.user_id != current_user.id:
		raise HTTPException(status_code=404, detail="Запись не найдена")
	
	session.delete(debt)
	session.commit()
	return None