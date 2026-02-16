from datetime import date
from decimal import Decimal
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
	
	# 1. Запрос курсов (Distinct on currency_id, сортировка по дате desc)
	stmt = (
		select(CurrencyRate, Currency)
		.join(Currency)
		.distinct(CurrencyRate.currency_id)
		.order_by(CurrencyRate.currency_id, CurrencyRate.date.desc())
	)
	
	results = session.exec(stmt).all()
	
	response_list = []
	
	# 2. Формируем ответ
	for rate_obj, currency_obj in results:
		response_list.append(CurrencyRateResponse(
			currency=currency_obj.char_code,
			name=currency_obj.name,
			rate=rate_obj.rate,  # Это цена за 1 единицу
			date=rate_obj.date
		))
	
	# 3. Добавляем базовую валюту UZS (которой нет в таблице rates, но она нужна фронту)
	# Находим или создаем объект для правильного нейминга, если нужно, или хардкодим
	response_list.insert(0, CurrencyRateResponse(
		currency="UZS",
		name="Узбекский сум",
		rate=Decimal("1.00"),
		date=date.today()
	))
	
	return response_list
