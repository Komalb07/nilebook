from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, date
from database import get_db
import models
from schemas import (
    RecurringTransactionCreate,
    RecurringTransactionCancel,
    RecurringTransactionConfirmCancel,
)
from auth import get_current_user
from difflib import SequenceMatcher
import re

router = APIRouter()

AUTO_CANCEL_MATCH_THRESHOLD = 0.82
POSSIBLE_MATCH_THRESHOLD = 0.55
ALLOWED_DIRECTIONS = {
    "expense",
    "income",
    "transfer",
    "loan_given",
    "loan_received",
    "gift_sent",
    "gift_received",
}
ALLOWED_FREQUENCIES = {"weekly", "biweekly", "monthly", "yearly", "custom_days"}


def normalize_recurring_name(value: str):
    if not value:
        return ""

    value = value.lower().strip()

    remove_words = [
        "subscription",
        "subscriptions",
        "membership",
        "memberships",
        "monthly",
        "weekly",
        "yearly",
        "annual",
        "annually",
        "plan",
        "premium",
        "payment",
        "payments",
        "recurring",
        "bill",
        "billing",
        "service",
        "services",
        "account",
        "my",
        "the",
        "a",
        "an",
        "for",
        "to",
        "from",
        "cancel",
        "cancelled",
        "canceled",
        "unsubscribe",
        "unsubscribed",
        "stopped",
        "using",
        "use",
        "quit",
        "resigned",
        "left",
        "job",
        "company",
        "contract",
        "ended",
        "terminated",
        "today",
    ]

    for word in remove_words:
        value = re.sub(rf"\b{word}\b", "", value)

    value = re.sub(r"[^a-z0-9]", "", value)

    return value


def get_similarity_score(a: str, b: str):
    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    if a in b or b in a:
        return 0.95

    return SequenceMatcher(None, a, b).ratio()


def find_best_recurring_match(active_rules, requested_name: str):
    normalized_requested_name = normalize_recurring_name(requested_name)

    scored_matches = []

    for rule in active_rules:
        normalized_rule_name = normalize_recurring_name(rule.name)

        score = get_similarity_score(
            normalized_requested_name,
            normalized_rule_name,
        )

        scored_matches.append(
            {
                "rule": rule,
                "score": score,
                "normalized_rule_name": normalized_rule_name,
            }
        )

    scored_matches = sorted(
        scored_matches,
        key=lambda item: item["score"],
        reverse=True,
    )

    if not scored_matches:
        return None, []

    best_match = scored_matches[0]

    possible_matches = [
        item
        for item in scored_matches
        if item["score"] >= POSSIBLE_MATCH_THRESHOLD
    ]

    return best_match, possible_matches


def recurring_rule_to_response(rule):
    return {
        "id": rule.id,
        "user_id": rule.user_id,
        "name": rule.name,
        "amount": rule.amount,
        "currency": rule.currency,
        "original_amount": rule.original_amount,
        "original_currency": rule.original_currency,
        "exchange_rate": rule.exchange_rate,
        "exchange_rate_date": rule.exchange_rate_date,
        "exchange_rate_source": rule.exchange_rate_source,
        "exchange_rate_fetched_at": rule.exchange_rate_fetched_at,
        "category": rule.category,
        "transaction_direction": rule.transaction_direction,
        "source": rule.source,
        "frequency": rule.frequency,
        "interval_days": rule.interval_days,
        "start_date": rule.start_date,
        "end_date": rule.end_date,
        "due_day": rule.due_day,
        "is_active": rule.is_active,
        "created_from_transaction_id": rule.created_from_transaction_id,
    }


def cancel_rule(rule, cancel_date: date, db: Session):
    rule.is_active = False
    rule.end_date = cancel_date
    rule.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(rule)

    return rule


@router.post("/recurring-transactions")
def create_recurring_transaction(
    recurring: RecurringTransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if recurring.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    recurring_name = recurring.name.strip()
    if not recurring_name or recurring_name.lower() == "unknown":
        raise HTTPException(status_code=400, detail="Recurring name is required")

    if recurring.amount < 0:
        raise HTTPException(status_code=400, detail="Amount must be zero or greater")

    if recurring.transaction_direction not in ALLOWED_DIRECTIONS:
        raise HTTPException(status_code=400, detail="Invalid transaction direction")

    if recurring.frequency not in ALLOWED_FREQUENCIES:
        raise HTTPException(status_code=400, detail="Invalid recurring frequency")

    interval_days = recurring.interval_days
    if recurring.frequency == "biweekly":
        interval_days = 14

    if recurring.frequency == "custom_days":
        if not interval_days or interval_days < 1:
            raise HTTPException(
                status_code=400,
                detail="Custom day-based recurrence requires interval_days",
            )
    elif recurring.frequency != "biweekly":
        interval_days = None

    new_rule = models.RecurringTransaction(
        user_id=recurring.user_id,
        name=recurring_name,
        amount=recurring.amount,
        currency=recurring.currency,
        original_amount=recurring.original_amount,
        original_currency=recurring.original_currency,
        exchange_rate=recurring.exchange_rate,
        exchange_rate_date=recurring.exchange_rate_date,
        exchange_rate_source=recurring.exchange_rate_source,
        exchange_rate_fetched_at=recurring.exchange_rate_fetched_at,
        category=recurring.category,
        transaction_direction=recurring.transaction_direction,
        source=recurring.source,
        frequency=recurring.frequency,
        interval_days=interval_days,
        start_date=recurring.start_date,
        due_day=recurring.due_day,
        is_active=True,
        created_from_transaction_id=recurring.created_from_transaction_id,
    )

    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)

    return {
        "message": "Recurring transaction created",
        "recurring_transaction": recurring_rule_to_response(new_rule),
    }


@router.get("/recurring-transactions/{user_id}")
def get_recurring_transactions(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    rules = (
        db.query(models.RecurringTransaction)
        .filter(models.RecurringTransaction.user_id == user_id)
        .order_by(models.RecurringTransaction.created_at.desc())
        .all()
    )

    return rules


@router.post("/recurring-transactions/cancel")
def cancel_recurring_transaction(
    request: RecurringTransactionCancel,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if request.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    active_rules = (
        db.query(models.RecurringTransaction)
        .filter(models.RecurringTransaction.user_id == request.user_id)
        .filter(models.RecurringTransaction.is_active == True)
        .all()
    )

    if not active_rules:
        raise HTTPException(
            status_code=404,
            detail="No active recurring transactions found",
        )

    best_match, possible_matches = find_best_recurring_match(
        active_rules,
        request.name,
    )

    if not best_match or best_match["score"] < POSSIBLE_MATCH_THRESHOLD:
        raise HTTPException(
            status_code=404,
            detail="No active recurring transaction found with this name",
        )

    if best_match["score"] < AUTO_CANCEL_MATCH_THRESHOLD:
        return {
            "message": "Possible recurring transaction matches found. Please confirm which one to cancel.",
            "requires_confirmation": True,
            "requested_name": request.name,
            "possible_matches": [
                {
                    "id": item["rule"].id,
                    "name": item["rule"].name,
                    "amount": item["rule"].amount,
                    "currency": item["rule"].currency,
                    "category": item["rule"].category,
                    "frequency": item["rule"].frequency,
                    "interval_days": item["rule"].interval_days,
                    "start_date": item["rule"].start_date,
                    "score": round(item["score"], 2),
                }
                for item in possible_matches
            ],
        }

    rule = cancel_rule(best_match["rule"], request.cancel_date, db)

    return {
        "message": "Recurring transaction cancelled",
        "requires_confirmation": False,
        "match_score": round(best_match["score"], 2),
        "recurring_transaction": {
            "id": rule.id,
            "name": rule.name,
            "end_date": rule.end_date,
            "is_active": rule.is_active,
        },
    }


@router.post("/recurring-transactions/{recurring_id}/confirm-cancel")
def confirm_cancel_recurring_transaction(
    recurring_id: str,
    request: RecurringTransactionConfirmCancel,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rule = (
        db.query(models.RecurringTransaction)
        .filter(models.RecurringTransaction.id == recurring_id)
        .first()
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")

    if request.user_id != current_user.id or rule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not rule.is_active:
        return {
            "message": "Recurring transaction is already cancelled",
            "recurring_transaction": {
                "id": rule.id,
                "name": rule.name,
                "end_date": rule.end_date,
                "is_active": rule.is_active,
            },
        }

    rule = cancel_rule(rule, request.cancel_date, db)

    return {
        "message": "Recurring transaction cancelled",
        "recurring_transaction": {
            "id": rule.id,
            "name": rule.name,
            "end_date": rule.end_date,
            "is_active": rule.is_active,
        },
    }


@router.delete("/recurring-transactions/{recurring_id}")
def delete_recurring_transaction(
    recurring_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rule = (
        db.query(models.RecurringTransaction)
        .filter(models.RecurringTransaction.id == recurring_id)
        .first()
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")

    if rule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(rule)
    db.commit()

    return {"message": "Recurring transaction deleted"}
