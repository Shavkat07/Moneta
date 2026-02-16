from datetime import date
from typing import List

from fastapi import Depends, HTTPException, APIRouter
from sqlmodel import Session, select

from app.core.database import get_session

from app.modules.finance.models import (
	Currency, CurrencyRate,
)
from app.modules.finance.schemas import CurrencyRateResponse
from app.modules.finance.services.currency_parser import CurrencyClient

# ==========================================
# 1. 💵 CURRENCY (Валюты)
# ==========================================

router = APIRouter()

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
	"""Берет строго последние курсы для каждой валюты"""
	
	statement = (
		select(CurrencyRate)
		# DISTINCT ON оставляет только первую строку из группы дубликатов
		.distinct(CurrencyRate.currency_id)
		# Сначала сортируем по ID валюты (требование DISTINCT ON в Postgres),
		# потом по дате (чтобы первая строка была самой свежей)
		.order_by(CurrencyRate.currency_id, CurrencyRate.date.desc())
	)
	
	rates = session.exec(statement).all()
	
	response = []
	for r in rates:
		# Обратите внимание: в вашей схеме CurrencyRateResponse (в schemas.py)
		# может не быть поля 'id', проверьте это.
		response.append(CurrencyRateResponse(
			currency=r.currency.char_code,
			rate=r.rate,
			date=r.date
		))
	
	uzs_currency = session.exec(select(Currency).where(Currency.char_code == "UZS")).first()
	
	if uzs_currency:
		# Добавляем фиктивную запись курса для UZS
		response.insert(0, CurrencyRateResponse(
			currency="UZS",
			rate=1.00,
			date=date.today()  # Дата - сегодня
		))
	
	return response