from typing import List

from sqladmin import ModelView
from wtforms import PasswordField, Form
from app.core.security import get_password_hash

from app.modules.auth.models import User


# --- 2. Настройка Видов (Как отображать таблицы) ---

class UserAdmin(ModelView, model=User):
	column_list = [User.phone_number, User.full_name, User.role, User.is_active, User.id, ]
	column_searchable_list = [User.phone_number, User.full_name]
	column_sortable_list = [User.created_at]
	icon = "fa-solid fa-user"
	
	form_columns = [
		User.phone_number,
		User.full_name,
		User.language_pref,
		User.role,
		User.is_active,
		User.is_verified
	]
	
	# 2. Переопределяем метод создания формы
	async def scaffold_form(self, rules: List[str] | None = None) -> type[Form]:
		# 1. Мы передаем rules дальше в родительский метод
		form_class = await super().scaffold_form(rules)
		
		# 2. Динамически добавляем поле пароля в полученный класс формы
		form_class.password = PasswordField("Password")
		
		return form_class
	
	async def on_model_change(self, data, model, is_created, request):
		incoming_password = data.pop("password")
		
		if is_created and not incoming_password:
			raise ValueError("Password is required for new users.")
		
		if incoming_password:
			model.hashed_password = get_password_hash(incoming_password)


