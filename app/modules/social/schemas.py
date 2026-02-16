from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel

from app.modules.social.models import DebtType, DebtStatus

# ==========================================
# Конфигурация для Decimal (как в finance)
# ==========================================
_money_model_config = ConfigDict(
	json_encoders={Decimal: lambda v: str(v)}
)


# ==========================================
# 1. 👤 DEBTOR (Должники / Контакты)
# ==========================================

class DebtorBase(SQLModel):
	name: str
	phone_number: Optional[str] = None


class DebtorCreate(DebtorBase):
	"""Схема для создания нового должника"""
	pass


class DebtorUpdate(SQLModel):
	"""Схема для обновления данных должника"""
	name: Optional[str] = None
	phone_number: Optional[str] = None


class DebtorRead(DebtorBase):
	"""Схема для ответа API"""
	id: int
	user_id: UUID
# Можно добавить вычисляемое поле, например, total_debt,
# но это лучше делать через query параметры или отдельный эндпоинт,
# чтобы не нагружать список.


# ==========================================
# 2. 📒 DEBT (Долги)
# ==========================================

class DebtBase(SQLModel):
	amount: Decimal
	currency_id: int
	type: DebtType = DebtType.GIVEN  # По умолчанию "Я дал"
	status: DebtStatus = DebtStatus.ACTIVE
	comment: Optional[str] = None
	due_date: Optional[datetime] = None


class DebtCreate(DebtBase):
	"""Схема для создания записи о долге"""
	debtor_id: int

# repaid_amount при создании обычно 0, поэтому не включаем сюда


class DebtUpdate(SQLModel):
	"""Схема для частичного редактирования"""
	amount: Optional[Decimal] = None
	repaid_amount: Optional[Decimal] = None
	status: Optional[DebtStatus] = None
	comment: Optional[str] = None
	due_date: Optional[datetime] = None


class DebtRead(DebtBase):
	"""Схема для просмотра долга (полная информация)"""
	model_config = _money_model_config
	
	id: int
	repaid_amount: Decimal
	created_at: datetime
	
	# Вложенный объект должника, чтобы на фронте сразу видеть имя
	# В SQLModel это подтянется, если в router сделать join или lazy loading
	debtor: Optional[DebtorRead] = None