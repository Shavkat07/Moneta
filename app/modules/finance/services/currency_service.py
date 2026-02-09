# app/modules/finance/services/currency_service.py
from decimal import Decimal
from sqlmodel import Session, select, desc
from app.modules.finance.models import Currency, CurrencyRate


class CurrencyService:
	def __init__(self, session: Session):
		self.session = session
	
	def get_rate_to_base(self, currency_id: int) -> Decimal:
		"""
		Возвращает стоимость 1 единицы валюты в базовой валюте (UZS).
		Логика:
		1. Если валюта UZS -> курс 1.
		2. Иначе ищем последнюю запись в CurrencyRate.
		"""
		currency = self.session.get(Currency, currency_id)
		if not currency:
			raise ValueError(f"Валюта с ID {currency_id} не найдена")
		
		# Если это базовый UZS, его курс всегда 1
		if currency.char_code == "UZS":
			return Decimal("1.00")
		
		# Ищем самый свежий курс
		statement = (
			select(CurrencyRate)
			.where(CurrencyRate.currency_id == currency_id)
			.order_by(desc(CurrencyRate.date))
		)
		rate_entry = self.session.exec(statement).first()
		
		if not rate_entry:
			raise ValueError(f"Не найден курс для валюты {currency.char_code}. Сначала обновите курсы.")
		
		return rate_entry.rate
	
	def convert(self, amount: Decimal, from_currency_id: int, to_currency_id: int) -> Decimal:
		"""
		Конвертирует сумму из одной валюты в другую.
		Формула: Amount * (Rate_From / Rate_To)
		"""
		if from_currency_id == to_currency_id:
			return amount
		
		rate_from = self.get_rate_to_base(from_currency_id)
		rate_to = self.get_rate_to_base(to_currency_id)
		
		# Считаем через кросс-курс (через UZS)
		# Пример: 100 USD -> EUR
		# 100 * (12500 / 13500) = 92.59 EUR
		converted_amount = amount * (rate_from / rate_to)
		
		return round(converted_amount, 2)