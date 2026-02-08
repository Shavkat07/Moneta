# app/core/database.py
from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

# check_same_thread=False нужен только для SQLite, для Postgres удаляем
engine = create_engine(settings.DATABASE_URL, echo=True) # echo=True выводит SQL запросы в консоль (удобно для отладки)

def get_session():
    """
    Генератор сессии. Открывает соединение, отдает его функции,
    а после завершения — закрывает.
    """
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    """
    Создает таблицы, если их нет.
    В продакшене лучше использовать Alembic, но для старта это ок.
    """
    SQLModel.metadata.create_all(engine)