# app/modules/finance/services/currency_service.py
from datetime import date as date_type
from decimal import Decimal
from typing import Optional
from sqlmodel import Session, select, desc
from app.modules.finance.models import Currency, CurrencyRate


class CurrencyService:
	def __init__(self, session: Session):
		self.session = session
	
	def get_rate_to_base(self, currency_id: int, date: Optional[date_type] = None) -> Decimal:
		"""
		Возвращает курс 1 единицы валюты к UZS.
		"""
		# Оптимизация: Сразу джойним валюту, чтобы проверить код
		currency = self.session.get(Currency, currency_id)
		if not currency:
			raise ValueError(f"Currency ID {currency_id} not found")
		
		if currency.char_code == "UZS":
			return Decimal("1.00")
		
		query = select(CurrencyRate.rate).where(CurrencyRate.currency_id == currency_id)
		
		if date:
			query = query.where(CurrencyRate.date <= date)
		
		# Берем самый свежий курс (на дату или последний вообще)
		query = query.order_by(CurrencyRate.date.desc())
		
		rate = self.session.exec(query).first()
		
		if rate is None:
			raise ValueError(f"No rate found for {currency.char_code}")
		
		return rate  # Это уже Decimal и уже за 1 единицу
	
	def convert(
			self,
			amount: Decimal,
			from_currency_id: int,
			to_currency_id: int,
			date: Optional[date_type] = None
	) -> Decimal:
		if from_currency_id == to_currency_id:
			return amount
		
		rate_from = self.get_rate_to_base(from_currency_id, date)
		rate_to = self.get_rate_to_base(to_currency_id, date)
		
		# Формула: (Сумма * Курс_Из) / Курс_В
		# Т.к. все курсы к UZS, это работает идеально.
		converted = (amount * rate_from) / rate_to
		
		# Округляем до 2 знаков только в самом конце
		return converted.quantize(Decimal("1.00"))