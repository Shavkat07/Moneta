from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.finance.models import Wallet, Currency
from app.modules.finance.schemas import WalletCreate, WalletRead

# ==========================================
# 3. 👛 WALLETS (Кошельки)
# ==========================================
router = APIRouter()


@router.post("/wallets", response_model=WalletRead, status_code=201, summary="Создать кошелек")
def create_wallet(
		wallet_in: WalletCreate,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# 1. Проверяем валюту
	statement = select(Currency).where(Currency.char_code == wallet_in.currency_code)
	currency = session.exec(statement).first()
	if not currency:
		raise HTTPException(status_code=404, detail=f"Валюта '{wallet_in.currency_code}' не найдена")
	
	# 2. Создаем кошелек, привязываем к юзеру
	wallet_data = wallet_in.model_dump(exclude={"currency_code"})
	
	wallet = Wallet(
		**wallet_in.model_dump(),
		currency_id=currency.id,
		user_id=current_user.id
	)
	
	session.add(wallet)
	session.commit()
	session.refresh(wallet)
	return wallet


@router.get("/wallets", response_model=List[WalletRead], summary="Мои кошельки")
def get_my_wallets(
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	# Показываем только кошельки текущего пользователя
	statement = select(Wallet).where(Wallet.user_id == current_user.id)
	wallets = session.exec(statement).all()
	
	response = []
	for w in wallets:
		# Для каждого кошелька берем код валюты через связь currency_rel
		# w.currency_rel.char_code автоматически сделает запрос в БД, если данные не подгружены
		code = w.currency_rel.char_code if w.currency_rel else "UNKNOWN"
		
		response.append(WalletRead(
			id=w.id,
			name=w.name,
			type=w.type,
			balance=w.balance,
			user_id=w.user_id,
			currency_code=code  # <--- Заполняем поле
		))
	return response


@router.get("/wallets/{wallet_id}", response_model=WalletRead)
def get_wallet_detail(
		wallet_id: int,
		session: Session = Depends(get_session),
		current_user: User = Depends(get_current_user)
):
	wallet = session.get(Wallet, wallet_id)
	if not wallet or wallet.user_id != current_user.id:
		raise HTTPException(status_code=404, detail="Кошелек не найден")
	
	code = wallet.currency_rel.char_code if wallet.currency_rel else "UNKNOWN"
	return WalletRead(
		id=wallet.id,
		name=wallet.name,
		type=wallet.type,
		balance=wallet.balance,
		user_id=wallet.user_id,
		currency_code=code
	)
