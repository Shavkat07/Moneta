# Переменные окружения и настройки
# app/core/config.py
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
	PROJECT_NAME: str = "Moneta API"
	
	# --- POSTGRES ---
	POSTGRES_USER: str
	POSTGRES_PASS: str
	POSTGRES_PORT: int
	POSTGRES_NAME: str
	POSTGRES_HOST: str
	
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
	
	def model_post_init(self, __context):
		self.DATABASE_URL = (
			f"postgresql://{self.POSTGRES_USER}:"
			f"{self.POSTGRES_PASS}@"
			f"{self.POSTGRES_HOST}:"
			f"{self.POSTGRES_PORT}/"
			f"{self.POSTGRES_NAME}"
		)


@lru_cache
def get_settings() -> Settings:
	return Settings()


settings = Settings()
