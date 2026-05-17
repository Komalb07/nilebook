from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user, verify_password
from currency_conversion import SUPPORTED_CURRENCIES
from schemas import DeleteAccountRequest
import models

router = APIRouter()


@router.put("/users/{user_id}/currency")
def update_currency(
    user_id: str,
    currency: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    normalized_currency = (currency or "").strip().upper()
    if normalized_currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail="Unsupported currency")

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.default_currency = normalized_currency
    db.commit()

    return {"message": "Currency updated", "currency": normalized_currency}


@router.delete("/users/{user_id}")
def delete_account(
    user_id: str,
    request: DeleteAccountRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    user = db.query(models.User).filter(models.User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    db.query(models.Transaction).filter(models.Transaction.user_id == user_id).delete()
    db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.user_id == user_id
    ).delete()

    db.delete(user)
    db.commit()

    return {"message": "Account deleted successfully"}
