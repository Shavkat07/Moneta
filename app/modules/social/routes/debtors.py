from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User


from app.modules.social.models import Debtor
from app.modules.social.schemas import (
	
	DebtorRead, DebtorCreate, DebtorUpdate)

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
