from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.finance.models import (
	Category
)
from app.modules.finance.schemas import (
	CategoryCreate, CategoryRead,
)

# ==========================================
# 2. 🗂 CATEGORIES (Категории)
# ==========================================
router = APIRouter()


@router.post("/categories", response_model=CategoryRead, summary="Создать категорию")
def create_category(
		category_in: CategoryCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)  # Требуем авторизацию
):
	# Можно добавить проверку: только админ может создавать глобальные категории
	category = Category.model_validate(category_in)
	session.add(category)
	session.commit()
	session.refresh(category)
	return category


@router.get("/categories", response_model=List[CategoryRead], summary="Список всех категорий")
def get_categories(
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# Получаем корневые категории (у которых нет родителя),
	# Pydantic схема сама подтянет детей (children), если они загружены
	# Для простоты пока отдаем плоский список или все сразу
	categories = session.exec(select(Category)).all()
	return categories
