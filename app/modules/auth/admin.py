from typing import Any, Dict
from starlette.requests import Request
from starlette_admin.contrib.sqla import ModelView
from starlette_admin.fields import (
	StringField,
	PasswordField,
	BooleanField,
	EnumField,
	PhoneField,
	DateTimeField,
	HasMany,
	FileField,
	EmailField
)
from starlette_admin.helpers import not_none
from starlette_admin.exceptions import FormValidationError
from app.core.security import get_password_hash
from app.modules.auth.models import UserRole, UserLanguage


class UserAdmin(ModelView):
	identity = "user"
	label = "Users"
	
	fields = [
		
		PhoneField("phone_number", label="Phone Number", placeholder="998901234567"),
		StringField("full_name", label="Full Name"),
		EmailField("email", label="Email"),
		# 1. Поле для СОЗДАНИЯ
		PasswordField(
			"password_create",
			label="Password",
			exclude_from_edit=True,
			exclude_from_list=True,
			exclude_from_detail=True
		),
		
		# 2. Поле для РЕДАКТИРОВАНИЯ
		PasswordField(
			"password_edit",
			label="Change Password",
			exclude_from_create=True,
			exclude_from_list=True,
			exclude_from_detail=True,
			placeholder="••••••••",
			help_text="Leave empty to keep the existing password."
		),
		
		# Реальный хеш (скрыт)
		StringField("hashed_password", exclude_from_create=True, exclude_from_edit=True, exclude_from_list=True,
		            exclude_from_detail=True),
		
		EnumField("role", label="Role", enum=UserRole),
		
		StringField("id", label="ID", exclude_from_create=True, exclude_from_edit=True),
		BooleanField("is_active", label="Active"),
		BooleanField("is_verified", label="Verified"),
		
		DateTimeField("created_at", label="Created At", exclude_from_create=True, exclude_from_edit=True),
		HasMany("wallets", label="Wallets", identity="wallet"),
		EnumField("language_pref", label="Language", enum=UserLanguage),
	]
	
	searchable_fields = ["full_name", "phone_number"]
	sortable_fields = ["created_at", "full_name"]
	exclude_fields_from_list = ["hashed_password", "updated_at"]
	
	# =========================================================================
	# ГЛАВНОЕ ИСПРАВЛЕНИЕ: ПЕРЕОПРЕДЕЛЕНИЕ POPULATE_OBJ
	# =========================================================================
	async def _populate_obj(
			self,
			request: Request,
			obj: Any,
			data: Dict[str, Any],
			is_edit: bool = False,
	) -> Any:
		# Проходимся по всем полям, которые есть в админке
		for field in self.get_fields_list(request, request.state.action):
			
			# --- ВОТ ЗДЕСЬ МЫ СПАСАЕМ СИТУАЦИЮ ---
			# Если поле - одно из наших виртуальных, мы просто пропускаем цикл.
			# Не вызываем setattr(), и SQLModel не падает с ошибкой.
			if field.name in ["password_create", "password_edit"]:
				continue
			# -------------------------------------
			
			name, value = field.name, data.get(field.name, None)
			
			# Стандартная логика библиотеки для остальных полей
			if isinstance(field, FileField):
				value, should_be_deleted = not_none(value)
				if should_be_deleted:
					setattr(obj, name, None)
				elif (not field.multiple and value is not None) or (
						field.multiple and isinstance(value, list) and len(value) > 0
				):
					setattr(obj, name, value)
			else:
				setattr(obj, name, value)
		
		return obj
	
	# =========================================================================
	# ХУКИ ДЛЯ ХЕШИРОВАНИЯ
	# =========================================================================
	
	async def before_create(self, request, data, obj):
		# obj здесь чистый, но _populate_obj вызовется ПОСЛЕ этого хука.
		# Поэтому мы можем смело брать данные из data и писать в obj.hashed_password
		
		raw_password = data.get("password_create")
		
		if not raw_password:
			raise FormValidationError({"password_create": "Password is required"})
		
		obj.hashed_password = get_password_hash(raw_password)
		return obj
	
	async def before_edit(self, request, data, obj):
		raw_password = data.get("password_edit")
		
		# Если пароль введен - обновляем хеш
		if raw_password:
			obj.hashed_password = get_password_hash(raw_password)
		
		return obj
	
