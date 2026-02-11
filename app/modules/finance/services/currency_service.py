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
		Возвращает стоимость 1 единицы валюты в базовой валюте (UZS).
		Логика:
		1. Если валюта UZS -> курс 1.
		2. Иначе ищем последнюю запись в CurrencyRate.
		
		Args:
			currency_id: ID валюты
			date: Опциональная дата для получения исторического курса.
			      Если не указана, возвращается последний доступный курс.
		"""
		currency = self.session.get(Currency, currency_id)
		if not currency:
			raise ValueError(f"Валюта с ID {currency_id} не найдена")
		
		# Если это базовый UZS, его курс всегда 1
		if currency.char_code == "UZS":
			return Decimal("1.00")
		
		# Строим запрос для поиска курса
		statement = (
			select(CurrencyRate)
			.where(CurrencyRate.currency_id == currency_id)
		)
		
		# Если указана дата, ищем курс на эту дату или ближайший предыдущий
		if date is not None:
			statement = statement.where(CurrencyRate.date <= date)
		
		# Сортируем по дате в обратном порядке и берем первый
		statement = statement.order_by(desc(CurrencyRate.date))
		rate_entry = self.session.exec(statement).first()
		
		if not rate_entry:
			if date is not None:
				raise ValueError(
					f"Не найден курс для валюты {currency.char_code} на дату {date} или ранее. "
					f"Сначала обновите курсы."
				)
			else:
				raise ValueError(f"Не найден курс для валюты {currency.char_code}. Сначала обновите курсы.")
		
		return rate_entry.rate
	
	def convert(
		self, 
		amount: Decimal, 
		from_currency_id: int, 
		to_currency_id: int,
		date: Optional[date_type] = None
	) -> Decimal:
		"""
		Конвертирует сумму из одной валюты в другую.
		Формула: Amount * (Rate_From / Rate_To)
		
		Args:
			amount: Сумма для конвертации
			from_currency_id: ID исходной валюты
			to_currency_id: ID целевой валюты
			date: Опциональная дата для использования исторического курса.
			      Если не указана, используется последний доступный курс.
		"""
		if from_currency_id == to_currency_id:
			return amount
		
		rate_from = self.get_rate_to_base(from_currency_id, date=date)
		rate_to = self.get_rate_to_base(to_currency_id, date=date)
		
		# Считаем через кросс-курс (через UZS)
		# Пример: 100 USD -> EUR
		# 100 * (12500 / 13500) = 92.59 EUR
		converted_amount = amount * (rate_from / rate_to)
		
		return round(converted_amount, 2)