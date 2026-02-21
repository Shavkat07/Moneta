from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, or_

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.finance.models import (
	Category
)
from app.modules.finance.schemas import (
	CategoryCreate, CategoryRead, CategoryUpdate,
)

router = APIRouter()


@router.post("", response_model=CategoryRead, summary="Создать категорию")
def create_category(
		category_in: CategoryCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)  # Требуем авторизацию
):
	existing = session.exec(
		select(Category).where(
			Category.name == category_in.name,
			Category.parent_id == category_in.parent_id,
			or_(Category.user_id == current_user.id, Category.user_id == None)
		)
	).first()
	
	if existing:
		raise HTTPException(status_code=400, detail="Категория с таким именем уже существует")
	
	category_data = category_in.model_dump()
	
	# 1. Принудительно назначаем владельца
	category_data["user_id"] = current_user.id
	
	# 2. Проверка parent_id (если указан, должен быть доступен юзеру)
	if category_data.get("parent_id"):
		parent = session.get(Category, category_data["parent_id"])
		if not parent or (parent.user_id and parent.user_id != current_user.id):
			raise HTTPException(status_code=400, detail="Родительская категория не найдена")
	
	category = Category(**category_data)
	session.add(category)
	session.commit()
	session.refresh(category)
	return category


@router.get("", response_model=List[CategoryRead], summary="Список всех категорий деревом")
def get_categories(
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# 1. Получаем из базы плоский список ТОЛЬКО разрешенных категорий
	# Это единственный запрос к БД.
	statement = select(Category).where(
		or_(
			Category.user_id == current_user.id,
			Category.user_id == None
		)
	)
	all_allowed_db = session.exec(statement).all()
	
	# 2. Создаем словарь схем, принудительно ОБНУЛЯЯ список children.
	# Это важно, чтобы Pydantic не подтянул старые связи из SQLAlchemy
	category_map: Dict[int, CategoryRead] = {}
	for c in all_allowed_db:
		category_map[c.id] = CategoryRead(
			id=c.id,
			name=c.name,
			type=c.type,
			icon_slug=c.icon_slug,
			parent_id=c.parent_id,
			user_id=c.user_id,
			children=[]  # Инициализируем пустым списком
		)
	
	tree: List[CategoryRead] = []
	
	# 3. Собираем дерево вручную
	for cat in category_map.values():
		if cat.parent_id is None:
			# Если нет родителя — это корень
			tree.append(cat)
		else:
			# Если родитель есть, ищем его в НАШЕМ отфильтрованном словаре
			parent = category_map.get(cat.parent_id)
			if parent:
				parent.children.append(cat)
			# Если parent_id есть, но родителя нет в словаре (он чужой),
			# то категория просто проигнорируется и не попадет в ответ.
	
	return tree


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
		category_id: int,
		category_in: CategoryUpdate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	db_category = session.get(Category, category_id)
	if not db_category:
		raise HTTPException(status_code=404, detail="Категория не найдена")
	
	# Запрещаем редактировать дефолтные категории (где user_id is None)
	if db_category.user_id is None:
		raise HTTPException(status_code=403, detail="Нельзя изменять системные категории")
	
	# Проверка владения
	if db_category.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Нет прав на редактирование этой категории")
	
	update_data = category_in.model_dump(exclude_unset=True)
	for key, value in update_data.items():
		setattr(db_category, key, value)
	
	session.add(db_category)
	session.commit()
	session.refresh(db_category)
	return db_category


@router.delete("/{category_id}")
def delete_category(
		category_id: int,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	db_category = session.get(Category, category_id)
	if not db_category:
		raise HTTPException(status_code=404, detail="Категория не найдена")
	
	if db_category.user_id is None:
		raise HTTPException(status_code=403, detail="Системные категории удалять нельзя")
	
	if db_category.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="Доступ запрещен")
	
	session.delete(db_category)
	session.commit()
	return {"ok": True}
