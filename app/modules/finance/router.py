from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.modules.finance.services.currency_parser import CurrencyClient
from app.modules.finance.schemas import CurrencyRateResponse
from app.modules.finance.models import CurrencyRate

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
	"""Берет последние курсы из БД"""
	# Логика: берем последние добавленные курсы.
	# В идеале нужно делать DISTINCT по валюте с сортировкой по дате,
	# но для простоты берем курсы за "сегодня" или просто последние 10 записей
	
	statement = select(CurrencyRate).order_by(CurrencyRate.date.desc()).limit(10)
	rates = session.exec(statement).all()
	
	# SQLModel автоматически подгрузит связанную валюту (rates.currency),
	# но так как мы отдаем плоскую схему, нужно маппить руками или делать join
	
	response = []
	for r in rates:
		# Важно: r.currency подгрузится лениво (lazy), так как в модели Relationship
		response.append(CurrencyRateResponse(
			currency=r.currency.char_code,
			rate=r.rate,
			date=r.date
		))
	return response