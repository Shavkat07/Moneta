from sqlmodel import Session, select
from app.modules.finance.models import Currency

def init_base_currency(session: Session):
    """Создает базовую валюту (UZS), если её нет"""
    statement = select(Currency).where(Currency.char_code == "UZS")
    uzs = session.exec(statement).first()

    if not uzs:
        print("🛠 Создание базовой валюты UZS...")
        uzs = Currency(
            code="860",          # ISO код узбекского сума
            char_code="UZS",
            name="Узбекский сум", # Или "Узбекский сум"
            nominal=1
        )
        session.add(uzs)
        session.commit()
        session.refresh(uzs)
        print("✅ UZS успешно добавлен.")