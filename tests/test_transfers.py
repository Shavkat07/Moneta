import pytest
from decimal import Decimal
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool
from app.modules.finance.models import Transaction, Wallet, Currency, TransactionType, WalletType
from app.modules.auth.models import User
from app.modules.finance.router import create_transaction, delete_transaction
from app.modules.finance.schemas import TransactionCreate

# Use in-memory SQLite with StaticPool to avoid threading/locking issues
@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="initial_data")
def initial_data_fixture(session: Session):
    user = User(
        email="test@example.com", 
        phone_number="1234567890",
        hashed_password="pw", 
        is_active=True, 
        is_superuser=False
    )
    session.add(user)
    
    currency = Currency(code="840", char_code="USD", name="Dollar", nominal=1)
    session.add(currency)
    
    session.commit()
    session.refresh(user)
    session.refresh(currency)
    
    wallet1 = Wallet(name="Wallet 1", balance=Decimal("1000.00"), currency_id=currency.id, user_id=user.id, type=WalletType.CASH)
    wallet2 = Wallet(name="Wallet 2", balance=Decimal("0.00"), currency_id=currency.id, user_id=user.id, type=WalletType.CASH)
    session.add(wallet1)
    session.add(wallet2)
    session.commit()
    session.refresh(wallet1)
    session.refresh(wallet2)
    return user, currency, wallet1, wallet2

def test_transfer_integrity(session: Session, initial_data):
    user, currency, wallet1, wallet2 = initial_data
    
    # 1. Create Transfer via Router
    amount = Decimal("100.00")
    t_create = TransactionCreate(
        wallet_id=wallet1.id,
        amount=amount,
        type=TransactionType.TRANSFER,
        target_wallet_id=wallet2.id,
        description="Transfer Test"
    )
    
    # Call the actual router function
    transaction = create_transaction(
        transaction_in=t_create,
        session=session,
        current_user=user
    )
    
    session.refresh(wallet1)
    session.refresh(wallet2)
    
    # Verify Balances
    assert wallet1.balance == Decimal("900.00")
    assert wallet2.balance == Decimal("100.00")
    
    # Verify Links
    assert transaction.related_transaction_id is not None
    related = session.get(Transaction, transaction.related_transaction_id)
    assert related is not None
    assert related.related_transaction_id == transaction.id
    
    # Verify Types
    assert transaction.type == TransactionType.TRANSFER
    assert related.type == TransactionType.INCOME
    
    # 2. Delete Transaction via Router
    delete_transaction(
        transaction_id=transaction.id,
        session=session,
        current_user=user
    )
    
    session.refresh(wallet1)
    session.refresh(wallet2)
    
    # Verify Balances Reverted
    assert wallet1.balance == Decimal("1000.00")
    assert wallet2.balance == Decimal("0.00")
    
    # Verify Deletion
    assert session.get(Transaction, transaction.id) is None
    assert session.get(Transaction, related.id) is None
