from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models
from schemas import TransactionCreate
from datetime import datetime

router = APIRouter()


def conversion_fields_from_model(transaction):
    return {
        "original_amount": transaction.original_amount,
        "original_currency": transaction.original_currency,
        "converted_amount": transaction.amount if transaction.original_currency else None,
        "converted_currency": transaction.currency if transaction.original_currency else None,
        "exchange_rate": transaction.exchange_rate,
        "exchange_rate_date": transaction.exchange_rate_date,
        "exchange_rate_source": transaction.exchange_rate_source,
        "exchange_rate_fetched_at": (
            transaction.exchange_rate_fetched_at.isoformat()
            if transaction.exchange_rate_fetched_at
            else None
        ),
        "requires_conversion_confirmation": False,
        "conversion_error": None,
    }


@router.post("/transactions")
def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    user = db.query(models.User).filter(models.User.id == transaction.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    duplicate = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == transaction.user_id)
        .filter(models.Transaction.date == transaction.date)
        .filter(models.Transaction.amount == transaction.amount)
        .filter(models.Transaction.category == transaction.category)
        .filter(models.Transaction.transaction_direction == transaction.transaction_direction)
        .filter(models.Transaction.counterparty == transaction.counterparty)
        .first()
    )

    if duplicate:
        raise HTTPException(status_code=409, detail="This transaction already exists")

    db_transaction = models.Transaction(
        user_id=transaction.user_id,
        raw_text=transaction.raw_text,
        date=transaction.date,
        amount=transaction.amount,
        currency=transaction.currency,
        original_amount=transaction.original_amount,
        original_currency=transaction.original_currency,
        exchange_rate=transaction.exchange_rate,
        exchange_rate_date=transaction.exchange_rate_date,
        exchange_rate_source=transaction.exchange_rate_source,
        exchange_rate_fetched_at=transaction.exchange_rate_fetched_at,
        sender=transaction.sender,
        receiver=transaction.receiver,
        counterparty=transaction.counterparty,
        category=transaction.category,
        transaction_direction=transaction.transaction_direction,
        source=transaction.source,
        origin_type=transaction.origin_type,
        status=transaction.status,
        is_recurring=transaction.is_recurring,
        confidence_score=transaction.confidence_score,
        review_level=transaction.review_level,
        transaction_subject=transaction.transaction_subject,
        subject_quality=transaction.subject_quality,
        missing_fields=transaction.missing_fields,
        ambiguity_reasons=transaction.ambiguity_reasons,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    return {
        "message": "Transaction saved",
        "transaction_id": db_transaction.id,
    }


@router.get("/transactions/{user_id}")
def get_transactions(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    transactions = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == user_id)
        .order_by(models.Transaction.created_at.desc())
        .all()
    )

    return [
        {
            "id": transaction.id,
            "user_id": transaction.user_id,
            "raw_text": transaction.raw_text,
            "date": str(transaction.date),
            "amount": transaction.amount,
            "currency": transaction.currency,
            **conversion_fields_from_model(transaction),
            "sender": transaction.sender,
            "receiver": transaction.receiver,
            "counterparty": transaction.counterparty,
            "category": transaction.category,
            "transaction_direction": transaction.transaction_direction,
            "source": transaction.source,
            "origin_type": transaction.origin_type,
            "status": transaction.status,
            "is_recurring": transaction.is_recurring,
            "confidence_score": transaction.confidence_score,
            "review_level": transaction.review_level,
            "transaction_subject": transaction.transaction_subject,
            "subject_quality": transaction.subject_quality,
            "missing_fields": transaction.missing_fields or [],
            "ambiguity_reasons": transaction.ambiguity_reasons or [],
            "created_at": str(transaction.created_at),
            "updated_at": str(transaction.updated_at),
        }
        for transaction in transactions
    ]


@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    transaction = (
        db.query(models.Transaction)
        .filter(models.Transaction.id == transaction_id)
        .first()
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    linked_recurring_rules = (
        db.query(models.RecurringTransaction)
        .filter(models.RecurringTransaction.user_id == current_user.id)
        .filter(models.RecurringTransaction.created_from_transaction_id == transaction_id)
        .all()
    )

    for rule in linked_recurring_rules:
        db.delete(rule)

    db.delete(transaction)
    db.commit()

    return {
        "message": "Transaction deleted",
        "deleted_recurring_rules": len(linked_recurring_rules),
    }


@router.put("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: str,
    transaction: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if transaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    existing_transaction = (
        db.query(models.Transaction)
        .filter(models.Transaction.id == transaction_id)
        .first()
    )

    if not existing_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if existing_transaction.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    existing_transaction.raw_text = transaction.raw_text
    existing_transaction.date = transaction.date
    existing_transaction.amount = transaction.amount
    existing_transaction.currency = transaction.currency
    existing_transaction.original_amount = transaction.original_amount
    existing_transaction.original_currency = transaction.original_currency
    existing_transaction.exchange_rate = transaction.exchange_rate
    existing_transaction.exchange_rate_date = transaction.exchange_rate_date
    existing_transaction.exchange_rate_source = transaction.exchange_rate_source
    existing_transaction.exchange_rate_fetched_at = transaction.exchange_rate_fetched_at
    existing_transaction.sender = transaction.sender
    existing_transaction.receiver = transaction.receiver
    existing_transaction.counterparty = transaction.counterparty
    existing_transaction.category = transaction.category
    existing_transaction.transaction_direction = transaction.transaction_direction
    existing_transaction.source = transaction.source
    existing_transaction.origin_type = transaction.origin_type
    existing_transaction.status = transaction.status
    existing_transaction.is_recurring = transaction.is_recurring
    existing_transaction.confidence_score = transaction.confidence_score
    existing_transaction.review_level = transaction.review_level
    existing_transaction.transaction_subject = transaction.transaction_subject
    existing_transaction.subject_quality = transaction.subject_quality
    existing_transaction.missing_fields = transaction.missing_fields
    existing_transaction.ambiguity_reasons = transaction.ambiguity_reasons
    existing_transaction.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(existing_transaction)

    return {
        "message": "Transaction updated",
        "transaction_id": existing_transaction.id,
    }
