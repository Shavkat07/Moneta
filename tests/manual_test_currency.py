#!/usr/bin/env python
"""Manual test script to verify currency service historical rate functionality"""

from datetime import date
from decimal import Decimal
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool
import sys
import os

# Add the project root to the path
sys.path.insert(0, '/home/shavkat/MEGA/Projects/Git_Clones/Moneta')

from app.modules.finance.models import Currency, CurrencyRate
from app.modules.finance.services.currency_service import CurrencyService


def setup_database():
    """Create test database with currencies and rates"""
    engine = create_engine(
        "sqlite:///:memory:", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


def create_test_data(session: Session):
    """Create test currencies and historical rates"""
    # Create currencies
    uzs = Currency(code="860", char_code="UZS", name="Uzbekistan Sum", nominal=1)
    usd = Currency(code="840", char_code="USD", name="US Dollar", nominal=1)
    eur = Currency(code="978", char_code="EUR", name="Euro", nominal=1)
    
    session.add_all([uzs, usd, eur])
    session.commit()
    session.refresh(uzs)
    session.refresh(usd)
    session.refresh(eur)
    
    # Create historical rates for USD
    rates = [
        CurrencyRate(currency_id=usd.id, rate=Decimal("12500.00"), date=date(2026, 1, 15)),
        CurrencyRate(currency_id=usd.id, rate=Decimal("12750.00"), date=date(2026, 2, 1)),
        CurrencyRate(currency_id=usd.id, rate=Decimal("12800.00"), date=date(2026, 2, 10)),
        CurrencyRate(currency_id=eur.id, rate=Decimal("13500.00"), date=date(2026, 1, 15)),
        CurrencyRate(currency_id=eur.id, rate=Decimal("13800.00"), date=date(2026, 2, 1)),
        CurrencyRate(currency_id=eur.id, rate=Decimal("14000.00"), date=date(2026, 2, 10)),
    ]
    session.add_all(rates)
    session.commit()
    
    return uzs, usd, eur


def main():
    print("=" * 70)
    print("TESTING CURRENCY SERVICE HISTORICAL RATE FUNCTIONALITY")
    print("=" * 70)
    
    engine = setup_database()
    
    with Session(engine) as session:
        uzs, usd, eur = create_test_data(session)
        service = CurrencyService(session)
        
        # Test 1: Get latest rate (no date parameter)
        print("\n✓ Test 1: Get latest USD rate (no date parameter)")
        latest_usd = service.get_rate_to_base(usd.id)
        print(f"  Expected: 12800.00, Got: {latest_usd}")
        assert latest_usd == Decimal("12800.00"), "Latest USD rate should be 12800.00"
        print("  PASSED ✓")
        
        # Test 2: Get historical rate (January 20, 2026)
        print("\n✓ Test 2: Get historical USD rate (Jan 20, 2026)")
        jan_usd = service.get_rate_to_base(usd.id, date=date(2026, 1, 20))
        print(f"  Expected: 12500.00, Got: {jan_usd}")
        assert jan_usd == Decimal("12500.00"), "Jan USD rate should be 12500.00"
        print("  PASSED ✓")
        
        # Test 3: Get historical rate (Feb 5, 2026)
        print("\n✓ Test 3: Get historical USD rate (Feb 5, 2026)")
        feb_usd = service.get_rate_to_base(usd.id, date=date(2026, 2, 5))
        print(f"  Expected: 12750.00, Got: {feb_usd}")
        assert feb_usd == Decimal("12750.00"), "Feb USD rate should be 12750.00"
        print("  PASSED ✓")
        
        # Test 4: UZS always returns 1.00
        print("\n✓ Test 4: UZS (base currency) always returns 1.00")
        uzs_rate = service.get_rate_to_base(uzs.id, date=date(2020, 1, 1))
        print(f"  Expected: 1.00, Got: {uzs_rate}")
        assert uzs_rate == Decimal("1.00"), "UZS rate should always be 1.00"
        print("  PASSED ✓")
        
        # Test 5: Convert using latest rates
        print("\n✓ Test 5: Convert 100 USD to EUR using latest rates")
        converted_latest = service.convert(Decimal("100.00"), usd.id, eur.id)
        print(f"  Expected: 91.43, Got: {converted_latest}")
        assert converted_latest == Decimal("91.43"), "Latest conversion should be 91.43"
        print("  PASSED ✓")
        
        # Test 6: Convert using historical rates (January)
        print("\n✓ Test 6: Convert 100 USD to EUR using January rates")
        converted_jan = service.convert(Decimal("100.00"), usd.id, eur.id, date=date(2026, 1, 20))
        print(f"  Expected: 92.59, Got: {converted_jan}")
        assert converted_jan == Decimal("92.59"), "January conversion should be 92.59"
        print("  PASSED ✓")
        
        # Test 7: Convert using historical rates (February)
        print("\n✓ Test 7: Convert 100 USD to EUR using February rates")
        converted_feb = service.convert(Decimal("100.00"), usd.id, eur.id, date=date(2026, 2, 5))
        print(f"  Expected: 92.39, Got: {converted_feb}")
        assert converted_feb == Decimal("92.39"), "February conversion should be 92.39"
        print("  PASSED ✓")
        
        # Test 8: Error handling - no rate before date
        print("\n✓ Test 8: Error when no rate exists before specified date")
        try:
            service.get_rate_to_base(usd.id, date=date(2026, 1, 1))
            print("  FAILED - Should have raised ValueError")
            sys.exit(1)
        except ValueError as e:
            print(f"  Correctly raised ValueError: {str(e)[:50]}...")
            print("  PASSED ✓")
        
        # Test 9: Same currency conversion
        print("\n✓ Test 9: Same currency conversion returns original amount")
        same_curr = service.convert(Decimal("100.00"), usd.id, usd.id)
        print(f"  Expected: 100.00, Got: {same_curr}")
        assert same_curr == Decimal("100.00"), "Same currency should return same amount"
        print("  PASSED ✓")
        
        # Test 10: Convert to UZS
        print("\n✓ Test 10: Convert 100 USD to UZS using January rate")
        to_uzs = service.convert(Decimal("100.00"), usd.id, uzs.id, date=date(2026, 1, 20))
        print(f"  Expected: 1250000.00, Got: {to_uzs}")
        assert to_uzs == Decimal("1250000.00"), "Conversion to UZS should be 1250000.00"
        print("  PASSED ✓")
        
        # Test 11: Convert from UZS
        print("\n✓ Test 11: Convert 1250000 UZS to USD using January rate")
        from_uzs = service.convert(Decimal("1250000.00"), uzs.id, usd.id, date=date(2026, 1, 20))
        print(f"  Expected: 100.00, Got: {from_uzs}")
        assert from_uzs == Decimal("100.00"), "Conversion from UZS should be 100.00"
        print("  PASSED ✓")
        
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED! ✓✓✓")
    print("=" * 70)
    print("\nSummary:")
    print("  • Historical rate retrieval: WORKING")
    print("  • Latest rate retrieval (backward compatibility): WORKING")
    print("  • Currency conversion with dates: WORKING")
    print("  • Error handling: WORKING")
    print("  • Base currency handling (UZS): WORKING")
    print("\nThe currency service now supports historical date-based rate lookups!")


if __name__ == "__main__":
    main()
