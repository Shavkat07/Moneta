# Переменные окружения и настройки
# app/core/config.py
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
	PROJECT_NAME: str = "Moneta API"
	
	# --- POSTGRES ---
	POSTGRES_USER: Optional[str] = None
	POSTGRES_PASS: Optional[str] = None
	POSTGRES_PORT: Optional[int] = None
	POSTGRES_NAME: Optional[str] = None
	POSTGRES_HOST: Optional[str] = None
	
	# --- DATABASE ---
	DATABASE_URL: str | None = None
	
	# --- PATHS ---
	BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
	
	# Безопасность (сгенерируй новый ключ: `openssl rand -hex 32`)
	JWT_SECRET_KEY: str
	ADMIN_SECRET_KEY: str
	ALGORITHM: str
	ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 дней (чтобы не логиниться постоянно)
	
	class Config:
		# Читаем переменные из файла .env
		env_file = ".env"
		case_sensitive = True
	
	@model_validator(mode='after')
	def assemble_db_connection(self) -> 'Settings':
		# Если DATABASE_URL уже пришел от Heroku, ничего не делаем
		if self.DATABASE_URL:
			# Heroku иногда присылает 'postgres://', SQLAlchemy требует 'postgresql://'
			if self.DATABASE_URL.startswith("postgres://"):
				self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
			return self
		
		# Если целой строки нет, собираем из компонентов
		if all([self.POSTGRES_USER, self.POSTGRES_PASS, self.POSTGRES_HOST, self.POSTGRES_PORT, self.POSTGRES_NAME]):
			self.DATABASE_URL = (
				f"postgresql://{self.POSTGRES_USER}:"
				f"{self.POSTGRES_PASS}@"
				f"{self.POSTGRES_HOST}:"
				f"{self.POSTGRES_PORT}/"
				f"{self.POSTGRES_NAME}"
			)
		else:
			raise ValueError("Необходимо указать либо DATABASE_URL, либо все компоненты POSTGRES_*")
		
		return self


@lru_cache
def get_settings() -> Settings:
	return Settings()


settings = Settings()
