import httpx
from decimal import Decimal
from datetime import datetime
from sqlmodel import Session, select

from app.modules.finance.models import Currency, CurrencyRate
from app.modules.finance.schemas import CbuCurrencyItem

# Убедись, что CurrencySchema тоже поддерживает Decimal или просто строку,
# но здесь мы берем данные напрямую из response.json() для чистоты примера.

CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"

TARGET_CURRENCIES = {"USD", "EUR", "RUB", "CNY", "GBP", "JPY", "CHF", "KRW", "AZN", "KZT"}


class CurrencyClient:
	async def fetch_rates(self) -> list[dict]:
		async with httpx.AsyncClient() as client:
			response = await client.get(CBU_URL)
			response.raise_for_status()
			return response.json()
	
	async def update_rates(self, session: Session):
		raw_data = await self.fetch_rates()
		updated_count = 0
		
		# 1. Загружаем все существующие валюты в словарь для быстрого поиска
		# Ключ: char_code ('USD'), Значение: Currency object
		existing_currencies = {
			c.char_code: c for c in session.exec(select(Currency)).all()
		}
		
		for item_dict in raw_data:
			# Валидируем и парсим через Pydantic (безопасно)
			try:
				cbu_item = CbuCurrencyItem(**item_dict)
			except Exception:
				continue  # Пропускаем битые данные
			
			if cbu_item.char_code not in TARGET_CURRENCIES:
				continue
			
			# --- Логика Валюты ---
			currency = existing_currencies.get(cbu_item.char_code)
			
			if not currency:
				# Создаем новую валюту
				currency = Currency(
					code=cbu_item.code,
					char_code=cbu_item.char_code,
					name=cbu_item.name_ru,
					nominal=cbu_item.nominal
				)
				session.add(currency)
				session.commit()
				session.refresh(currency)
				# Добавляем в локальный кэш
				existing_currencies[cbu_item.char_code] = currency
			else:
				# Обновляем номинал, если вдруг ЦБ его изменил
				if currency.nominal != cbu_item.nominal:
					currency.nominal = cbu_item.nominal
					session.add(currency)
			
			# --- Логика Курса (САМОЕ ВАЖНОЕ) ---
			# Нормализация: Вычисляем цену за 1 единицу
			# Пример: ЦБ дает JPY Nominal=10, Rate=800. Значит реальный курс 1 JPY = 80.
			normalized_rate = cbu_item.rate / Decimal(cbu_item.nominal)
			
			# Проверяем, есть ли уже курс на эту дату
			# (Можно оптимизировать, загрузив и рейты в память, но дат много, лучше точечно)
			stmt_check = select(CurrencyRate).where(
				CurrencyRate.currency_id == currency.id,
				CurrencyRate.date == cbu_item.parsed_date
			)
			existing_rate = session.exec(stmt_check).first()
			
			if not existing_rate:
				new_rate = CurrencyRate(
					currency_id=currency.id,
					rate=normalized_rate,  # Пишем "чистый" курс
					date=cbu_item.parsed_date
				)
				session.add(new_rate)
				updated_count += 1
		
		session.commit()
		return {"status": "success", "new_rates_added": updated_count}