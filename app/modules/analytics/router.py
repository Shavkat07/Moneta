from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from datetime import date, timedelta
from typing import List
from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.finance.models import Transaction, TransactionType, Category

router = APIRouter()


@router.get("/summary")
def get_monthly_summary(
		month: date = None,  # Если нет, берем текущий
		session: Session = Depends(get_session),
		user: User = Depends(get_current_user)
):
	"""Возвращает: Общий доход, Общий расход, Разницу (Savings) за месяц"""
	if not month:
		month = date.today()
	
	# Определяем начало и конец месяца
	start_date = month.replace(day=1)
	next_month = (start_date + timedelta(days=32)).replace(day=1)
	
	# SQL запрос: Группируем по типу транзакции (INCOME/EXPENSE)
	# ВАЖНО: Тут нужно учитывать валюты! Для MVP пока считаем в валюте кошелька
	# (или нужно конвертировать всё к базовой валюте UZS через CurrencyService)
	
	query = (
		select(Transaction.type, func.sum(Transaction.amount))
		.join(Transaction.wallet)
		.where(Transaction.wallet.has(user_id=user.id))
		.where(Transaction.created_at >= start_date)
		.where(Transaction.created_at < next_month)
		.group_by(Transaction.type)
	)
	
	results = session.exec(query).all()
	
	summary = {"income": 0, "expense": 0, "total": 0}
	for t_type, amount in results:
		if t_type == TransactionType.INCOME:
			summary["income"] = amount
		elif t_type == TransactionType.EXPENSE:
			summary["expense"] = amount
	
	summary["total"] = summary["income"] - summary["expense"]
	return summary


@router.get("/expenses-by-category")
def get_expenses_by_category(
		session: Session = Depends(get_session),
		user: User = Depends(get_current_user)
):
	"""Для круговой диаграммы расходов"""
	query = (
		select(Category.name, func.sum(Transaction.amount))
		.join(Transaction.category)
		.join(Transaction.wallet)
		.where(Transaction.wallet.has(user_id=user.id))
		.where(Transaction.type == TransactionType.EXPENSE)
		.group_by(Category.name)
	)
	results = session.exec(query).all()
	
	return [{"category": name, "amount": amount} for name, amount in results]