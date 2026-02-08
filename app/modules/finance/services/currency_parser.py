import httpx
from decimal import Decimal
from datetime import datetime
from sqlmodel import Session, select

from app.modules.finance.models import Currency, CurrencyRate

# Убедись, что CurrencySchema тоже поддерживает Decimal или просто строку,
# но здесь мы берем данные напрямую из response.json() для чистоты примера.

CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"


class CurrencyClient:
	async def fetch_rates(self):
		async with httpx.AsyncClient() as client:
			response = await client.get(CBU_URL)
			response.raise_for_status()
			return response.json()
	
	async def update_rates(self, session: Session):
		raw_data = await self.fetch_rates()
		updated_count = 0
		
		# Основные валюты для отслеживания
		target_char_codes = ["USD", "EUR", "RUB", "CNY", "GBP", "JPY", "CHF", "KRW", "AZN", "KZT"]
		
		for item in raw_data:
			# Получаем код валюты (например, "USD")
			code_char = item.get("Ccy")
			
			if code_char not in target_char_codes:
				continue
			
			# 1. Поиск валюты в БД
			statement = select(Currency).where(Currency.char_code == code_char)
			currency = session.exec(statement).first()
			
			# Если валюты нет - создаем
			if not currency:
				currency = Currency(
					code=item.get("Code"),
					char_code=code_char,
					name=item.get("CcyNm_RU"),  # Или CcyNm_UZ, если хочешь на узбекском
					nominal=int(item.get("Nominal"))
				)
				session.add(currency)
				session.commit()
				session.refresh(currency)
			
			# 2. Обработка данных (Дата и Курс)
			rate_date = datetime.strptime(item.get("Date"), "%d.%m.%Y").date()
			
			# ВАЖНО: Конвертируем строку сразу в Decimal
			rate_value = Decimal(item.get("Rate"))
			
			# 3. Проверка на дубликат (чтобы не записывать курс дважды за один день)
			stmt_rate = select(CurrencyRate).where(
				CurrencyRate.currency_id == currency.id,
				CurrencyRate.date == rate_date
			)
			existing_rate = session.exec(stmt_rate).first()
			
			if not existing_rate:
				new_rate = CurrencyRate(
					currency_id=currency.id,
					rate=rate_value,
					date=rate_date
				)
				session.add(new_rate)
				updated_count += 1
		
		session.commit()
		return {"status": "success", "new_rates_added": updated_count}