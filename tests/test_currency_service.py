import pytest
from datetime import date
from decimal import Decimal
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool
from app.modules.finance.models import Currency, CurrencyRate
from app.modules.finance.services.currency_service import CurrencyService


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


@pytest.fixture(name="test_currencies")
def test_currencies_fixture(session: Session):
    """Create test currencies: UZS (base), USD, EUR"""
    uzs = Currency(code="860", char_code="UZS", name="Uzbekistan Sum", nominal=1)
    usd = Currency(code="840", char_code="USD", name="US Dollar", nominal=1)
    eur = Currency(code="978", char_code="EUR", name="Euro", nominal=1)
    
    session.add(uzs)
    session.add(usd)
    session.add(eur)
    session.commit()
    
    session.refresh(uzs)
    session.refresh(usd)
    session.refresh(eur)
    
    return uzs, usd, eur


@pytest.fixture(name="historical_rates")
def historical_rates_fixture(session: Session, test_currencies):
    """Create historical currency rates for testing"""
    uzs, usd, eur = test_currencies
    
    # Historical rates for USD (against UZS)
    # January 2026: 1 USD = 12500 UZS
    rate_usd_jan = CurrencyRate(
        currency_id=usd.id,
        rate=Decimal("12500.00"),
        date=date(2026, 1, 15)
    )
    
    # February 2026: 1 USD = 12750 UZS (appreciation)
    rate_usd_feb = CurrencyRate(
        currency_id=usd.id,
        rate=Decimal("12750.00"),
        date=date(2026, 2, 1)
    )
    
    # Latest (February 10): 1 USD = 12800 UZS
    rate_usd_latest = CurrencyRate(
        currency_id=usd.id,
        rate=Decimal("12800.00"),
        date=date(2026, 2, 10)
    )
    
    # Historical rates for EUR (against UZS)
    # January 2026: 1 EUR = 13500 UZS
    rate_eur_jan = CurrencyRate(
        currency_id=eur.id,
        rate=Decimal("13500.00"),
        date=date(2026, 1, 15)
    )
    
    # February 2026: 1 EUR = 13800 UZS
    rate_eur_feb = CurrencyRate(
        currency_id=eur.id,
        rate=Decimal("13800.00"),
        date=date(2026, 2, 1)
    )
    
    # Latest (February 10): 1 EUR = 14000 UZS
    rate_eur_latest = CurrencyRate(
        currency_id=eur.id,
        rate=Decimal("14000.00"),
        date=date(2026, 2, 10)
    )
    
    session.add_all([
        rate_usd_jan, rate_usd_feb, rate_usd_latest,
        rate_eur_jan, rate_eur_feb, rate_eur_latest
    ])
    session.commit()
    
    return {
        'usd_jan': rate_usd_jan,
        'usd_feb': rate_usd_feb,
        'usd_latest': rate_usd_latest,
        'eur_jan': rate_eur_jan,
        'eur_feb': rate_eur_feb,
        'eur_latest': rate_eur_latest,
    }


def test_get_rate_to_base_latest(session: Session, test_currencies, historical_rates):
    """Test that calling without date parameter returns the latest rate"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    # Without date, should return latest rate
    usd_rate = service.get_rate_to_base(usd.id)
    assert usd_rate == Decimal("12800.00")
    
    eur_rate = service.get_rate_to_base(eur.id)
    assert eur_rate == Decimal("14000.00")


def test_get_rate_to_base_historical(session: Session, test_currencies, historical_rates):
    """Test that calling with a specific date returns the rate valid on that date"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    # January 20, 2026 - should get January 15 rate (most recent before Jan 20)
    usd_rate_jan = service.get_rate_to_base(usd.id, date=date(2026, 1, 20))
    assert usd_rate_jan == Decimal("12500.00")
    
    # February 5, 2026 - should get February 1 rate
    usd_rate_feb = service.get_rate_to_base(usd.id, date=date(2026, 2, 5))
    assert usd_rate_feb == Decimal("12750.00")
    
    # Exact date match - February 10, 2026
    usd_rate_exact = service.get_rate_to_base(usd.id, date=date(2026, 2, 10))
    assert usd_rate_exact == Decimal("12800.00")


def test_get_rate_to_base_no_rate_for_date(session: Session, test_currencies, historical_rates):
    """Test error handling when no rate exists on or before the specified date"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    # Try to get rate for a date before any rates exist
    with pytest.raises(ValueError, match="Не найден курс для валюты USD на дату 2026-01-01"):
        service.get_rate_to_base(usd.id, date=date(2026, 1, 1))


def test_get_rate_to_base_uzs_always_one(session: Session, test_currencies, historical_rates):
    """Test UZS (base currency) always returns 1.00 regardless of date"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    # Without date
    assert service.get_rate_to_base(uzs.id) == Decimal("1.00")
    
    # With historical date
    assert service.get_rate_to_base(uzs.id, date=date(2026, 1, 15)) == Decimal("1.00")
    
    # With any date
    assert service.get_rate_to_base(uzs.id, date=date(2020, 1, 1)) == Decimal("1.00")


def test_convert_same_currency(session: Session, test_currencies, historical_rates):
    """Test conversion with same source and target currency returns original amount"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    amount = Decimal("100.00")
    
    # Same currency, no date
    assert service.convert(amount, usd.id, usd.id) == amount
    
    # Same currency, with date
    assert service.convert(amount, usd.id, usd.id, date=date(2026, 1, 15)) == amount


def test_convert_latest_rates(session: Session, test_currencies, historical_rates):
    """Test conversion using latest rates (no date parameter)"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    # Convert 100 USD to EUR using latest rates
    # Latest: 1 USD = 12800 UZS, 1 EUR = 14000 UZS
    # Formula: 100 * (12800 / 14000) = 91.43 EUR
    amount = Decimal("100.00")
    converted = service.convert(amount, usd.id, eur.id)
    
    expected = Decimal("91.43")  # 100 * (12800 / 14000) = 91.42857... rounded to 91.43
    assert converted == expected


def test_convert_historical_rates(session: Session, test_currencies, historical_rates):
    """Test conversion using historical rates (with date parameter)"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    # Convert 100 USD to EUR using January rates
    # January: 1 USD = 12500 UZS, 1 EUR = 13500 UZS
    # Formula: 100 * (12500 / 13500) = 92.59 EUR
    amount = Decimal("100.00")
    converted_jan = service.convert(amount, usd.id, eur.id, date=date(2026, 1, 20))
    
    expected_jan = Decimal("92.59")  # 100 * (12500 / 13500) = 92.592... rounded to 92.59
    assert converted_jan == expected_jan


def test_convert_with_different_historical_dates(session: Session, test_currencies, historical_rates):
    """Test that different results are returned for different historical dates"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    amount = Decimal("100.00")
    
    # January conversion
    converted_jan = service.convert(amount, usd.id, eur.id, date=date(2026, 1, 20))
    
    # February conversion
    converted_feb = service.convert(amount, usd.id, eur.id, date=date(2026, 2, 5))
    
    # Latest conversion (no date)
    converted_latest = service.convert(amount, usd.id, eur.id)
    
    # All three should be different due to different exchange rates
    assert converted_jan != converted_feb
    assert converted_feb != converted_latest
    assert converted_jan != converted_latest
    
    # Verify expected values
    # Jan: 100 * (12500 / 13500) = 92.59
    # Feb: 100 * (12750 / 13800) = 92.39
    # Latest: 100 * (12800 / 14000) = 91.43
    assert converted_jan == Decimal("92.59")
    assert converted_feb == Decimal("92.39")
    assert converted_latest == Decimal("91.43")


def test_convert_to_uzs(session: Session, test_currencies, historical_rates):
    """Test conversion from foreign currency to UZS"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    # Convert 100 USD to UZS using January rate
    # January: 1 USD = 12500 UZS
    # Formula: 100 * (12500 / 1) = 1250000 UZS
    amount = Decimal("100.00")
    converted = service.convert(amount, usd.id, uzs.id, date=date(2026, 1, 20))
    
    expected = Decimal("1250000.00")
    assert converted == expected


def test_convert_from_uzs(session: Session, test_currencies, historical_rates):
    """Test conversion from UZS to foreign currency"""
    uzs, usd, eur = test_currencies
    service = CurrencyService(session)
    
    # Convert 1250000 UZS to USD using January rate
    # January: 1 USD = 12500 UZS
    # Formula: 1250000 * (1 / 12500) = 100 USD
    amount = Decimal("1250000.00")
    converted = service.convert(amount, uzs.id, usd.id, date=date(2026, 1, 20))
    
    expected = Decimal("100.00")
    assert converted == expected
