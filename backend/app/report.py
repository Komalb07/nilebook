from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user
import models
from datetime import date, timedelta
import calendar

router = APIRouter()

MONEY_IN_DIRECTIONS = {"income", "loan_received", "gift_received"}
MONEY_OUT_DIRECTIONS = {"expense", "loan_given", "gift_sent"}


def get_week_ranges_for_month(year: int, month: int):
    last_day = calendar.monthrange(year, month)[1]

    week_ranges = [
        {"week": 1, "start_day": 1, "end_day": 7},
        {"week": 2, "start_day": 8, "end_day": 14},
        {"week": 3, "start_day": 15, "end_day": 21},
        {"week": 4, "start_day": 22, "end_day": 28},
    ]

    if last_day > 28:
        week_ranges.append({"week": 5, "start_day": 29, "end_day": last_day})

    return week_ranges


def get_week_range(year: int, month: int, week: int):
    for week_range in get_week_ranges_for_month(year, month):
        if week_range["week"] == week:
            return week_range
    return None


def calculate_money_summary(items):
    total_money_in = sum(
        item["amount"]
        for item in items
        if item["transaction_direction"] in MONEY_IN_DIRECTIONS
    )

    total_money_out = sum(
        item["amount"]
        for item in items
        if item["transaction_direction"] in MONEY_OUT_DIRECTIONS
    )

    return total_money_in, total_money_out, total_money_in - total_money_out


def transaction_to_dict(t):
    return {
        "id": t.id,
        "raw_text": t.raw_text,
        "date": str(t.date),
        "amount": t.amount,
        "currency": t.currency,
        "original_amount": t.original_amount,
        "original_currency": t.original_currency,
        "converted_amount": t.amount if t.original_currency else None,
        "converted_currency": t.currency if t.original_currency else None,
        "exchange_rate": t.exchange_rate,
        "exchange_rate_date": t.exchange_rate_date,
        "exchange_rate_source": t.exchange_rate_source,
        "exchange_rate_fetched_at": (
            t.exchange_rate_fetched_at.isoformat()
            if t.exchange_rate_fetched_at
            else None
        ),
        "requires_conversion_confirmation": False,
        "conversion_error": None,
        "sender": t.sender,
        "receiver": t.receiver,
        "counterparty": t.counterparty,
        "category": t.category,
        "transaction_direction": t.transaction_direction,
        "source": t.source,
        "origin_type": t.origin_type,
        "status": t.status,
        "is_recurring": t.is_recurring,
        "confidence_score": t.confidence_score,
        "review_level": t.review_level,
        "transaction_subject": t.transaction_subject,
        "subject_quality": t.subject_quality,
        "missing_fields": t.missing_fields or [],
        "ambiguity_reasons": t.ambiguity_reasons or [],
    }


def recurring_to_dict(rule, occurrence_date: date):
    money_in = rule.transaction_direction in MONEY_IN_DIRECTIONS
    money_out = rule.transaction_direction in MONEY_OUT_DIRECTIONS

    sender = rule.name if money_in else "Me"
    receiver = "Me" if money_in else rule.name

    if not money_in and not money_out:
        sender = rule.name
        receiver = rule.name

    return {
        "id": f"recurring-{rule.id}-{occurrence_date.isoformat()}",
        "raw_text": f"{rule.name} recurring transaction",
        "date": str(occurrence_date),
        "amount": rule.amount,
        "currency": rule.currency,
        "original_amount": getattr(rule, "original_amount", None),
        "original_currency": getattr(rule, "original_currency", None),
        "converted_amount": (
            rule.amount if getattr(rule, "original_currency", None) else None
        ),
        "converted_currency": (
            rule.currency if getattr(rule, "original_currency", None) else None
        ),
        "exchange_rate": getattr(rule, "exchange_rate", None),
        "exchange_rate_date": getattr(rule, "exchange_rate_date", None),
        "exchange_rate_source": getattr(rule, "exchange_rate_source", None),
        "exchange_rate_fetched_at": (
            getattr(rule, "exchange_rate_fetched_at", None).isoformat()
            if getattr(rule, "exchange_rate_fetched_at", None)
            else None
        ),
        "requires_conversion_confirmation": False,
        "conversion_error": None,
        "sender": sender,
        "receiver": receiver,
        "counterparty": rule.name,
        "category": rule.category,
        "transaction_direction": rule.transaction_direction,
        "source": rule.source,
        "origin_type": "recurring",
        "status": "projected",
        "is_recurring": True,
        "confidence_score": 1.0,
        "review_level": "none",
        "transaction_subject": rule.name,
        "subject_quality": "clear",
        "missing_fields": [],
        "ambiguity_reasons": [],
    }


def is_occurrence_in_rule_window(rule, occurrence_date: date):
    if not rule.start_date:
        return False

    if occurrence_date < rule.start_date:
        return False

    if rule.end_date and occurrence_date > rule.end_date:
        return False

    return True


def get_monthly_occurrence_date(rule, year: int, month: int):
    due_day_raw = rule.due_day or str(rule.start_date.day)

    try:
        due_day = int(due_day_raw)
    except Exception:
        due_day = rule.start_date.day

    last_day = calendar.monthrange(year, month)[1]
    due_day = min(due_day, last_day)

    occurrence_date = date(year, month, due_day)

    if not is_occurrence_in_rule_window(rule, occurrence_date):
        return []

    return [occurrence_date]


def get_weekly_occurrence_dates(rule, year: int, month: int):
    return get_interval_occurrence_dates(rule, year, month, 7)


def get_interval_occurrence_dates(rule, year: int, month: int, interval_days: int):
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    occurrence_date = rule.start_date
    while occurrence_date < first_day:
        missed_days = (first_day - occurrence_date).days
        intervals_to_advance = max(1, missed_days // interval_days)
        occurrence_date = occurrence_date + timedelta(
            days=intervals_to_advance * interval_days
        )

    while occurrence_date < first_day:
        occurrence_date = occurrence_date + timedelta(days=interval_days)

    occurrences = []
    while occurrence_date <= last_day:
        if is_occurrence_in_rule_window(rule, occurrence_date):
            occurrences.append(occurrence_date)
        occurrence_date = occurrence_date + timedelta(days=interval_days)

    return occurrences


def get_yearly_occurrence_date(rule, year: int, month: int):
    if rule.start_date.month != month:
        return []

    last_day = calendar.monthrange(year, month)[1]
    occurrence_date = date(year, month, min(rule.start_date.day, last_day))

    if not is_occurrence_in_rule_window(rule, occurrence_date):
        return []

    return [occurrence_date]


def get_recurring_occurrence_dates(rule, year: int, month: int):
    if rule.frequency == "monthly":
        return get_monthly_occurrence_date(rule, year, month)

    if rule.frequency == "weekly":
        return get_weekly_occurrence_dates(rule, year, month)

    if rule.frequency == "biweekly":
        return get_interval_occurrence_dates(rule, year, month, 14)

    if rule.frequency == "custom_days":
        interval_days = rule.interval_days or 0
        if interval_days < 1:
            return []
        return get_interval_occurrence_dates(rule, year, month, interval_days)

    if rule.frequency == "yearly":
        return get_yearly_occurrence_date(rule, year, month)

    return []


def is_duplicate_created_from_occurrence(rule, occurrence_date: date, actual_items):
    if not rule.created_from_transaction_id:
        return False

    return any(
        item["id"] == rule.created_from_transaction_id
        and date.fromisoformat(item["date"]) == occurrence_date
        for item in actual_items
    )


def get_recurring_items_for_month(
    user_id: str,
    year: int,
    month: int,
    db: Session,
    actual_items=None,
):
    rules = (
        db.query(models.RecurringTransaction)
        .filter(models.RecurringTransaction.user_id == user_id)
        .all()
    )

    recurring_items = []
    actual_items = actual_items or []

    for rule in rules:
        if not rule.is_active and not rule.end_date:
            continue

        occurrence_dates = get_recurring_occurrence_dates(rule, year, month)

        for occurrence_date in occurrence_dates:
            if is_duplicate_created_from_occurrence(rule, occurrence_date, actual_items):
                continue

            recurring_items.append(recurring_to_dict(rule, occurrence_date))

    return recurring_items


def get_actual_items_for_user(user_id: str, db: Session):
    transactions = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == user_id)
        .all()
    )

    return [transaction_to_dict(t) for t in transactions]


def filter_items_by_year(items, year: int):
    return [item for item in items if date.fromisoformat(item["date"]).year == year]


def filter_items_by_month(items, year: int, month: int):
    return [
        item
        for item in items
        if date.fromisoformat(item["date"]).year == year
        and date.fromisoformat(item["date"]).month == month
    ]


def filter_items_by_week(items, year: int, month: int, start_day: int, end_day: int):
    return [
        item
        for item in items
        if date.fromisoformat(item["date"]).year == year
        and date.fromisoformat(item["date"]).month == month
        and start_day <= date.fromisoformat(item["date"]).day <= end_day
    ]


def get_all_items_for_month(user_id: str, year: int, month: int, db: Session):
    actual_items = get_actual_items_for_user(user_id, db)
    month_actual_items = filter_items_by_month(actual_items, year, month)
    recurring_items = get_recurring_items_for_month(
        user_id,
        year,
        month,
        db,
        month_actual_items,
    )

    return month_actual_items + recurring_items


def get_all_items_for_year(user_id: str, year: int, db: Session):
    actual_items = get_actual_items_for_user(user_id, db)
    year_actual_items = filter_items_by_year(actual_items, year)

    today = date.today()
    if year < today.year:
        recurring_months = range(1, 13)
    elif year == today.year:
        recurring_months = range(1, today.month + 1)
    else:
        recurring_months = []

    recurring_items = []
    for month in recurring_months:
        month_actual_items = filter_items_by_month(actual_items, year, month)
        recurring_items.extend(
            get_recurring_items_for_month(
                user_id,
                year,
                month,
                db,
                month_actual_items,
            )
        )

    return year_actual_items + recurring_items


def get_recurring_report_years(user_id: str, db: Session):
    current_year = date.today().year
    rules = (
        db.query(models.RecurringTransaction.start_date, models.RecurringTransaction.end_date)
        .filter(models.RecurringTransaction.user_id == user_id)
        .all()
    )

    years = set()
    for start_date, end_date in rules:
        if not start_date:
            continue

        end_year = min(end_date.year if end_date else current_year, current_year)

        if start_date.year > end_year:
            continue

        years.update(range(start_date.year, end_year + 1))

    return years


@router.get("/report/{user_id}/years")
def get_report_years(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    transactions = (
        db.query(models.Transaction.date)
        .filter(models.Transaction.user_id == user_id)
        .all()
    )

    actual_years = {transaction_date.year for (transaction_date,) in transactions}
    recurring_years = get_recurring_report_years(user_id, db)

    years = sorted(actual_years | recurring_years, reverse=True)

    return {"years": years}


@router.get("/report/{user_id}/{year}")
def get_year_report(
    user_id: str,
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    year_items = get_all_items_for_year(user_id, year, db)

    total_money_in, total_money_out, net_flow = calculate_money_summary(year_items)

    current_year = date.today().year
    is_completed_year = year < current_year

    if is_completed_year:
        available_months = list(range(1, 13))
    elif year == current_year:
        available_months = list(range(1, date.today().month + 1))
    else:
        available_months = []

    return {
        "year": year,
        "title": f"{year} Finance Report",
        "is_completed_year": is_completed_year,
        "is_ongoing_year": year == current_year,
        "summary_label": "" if is_completed_year else "So far...",
        "total_money_in": total_money_in,
        "total_money_out": total_money_out,
        "net_flow": net_flow,
        "available_months": available_months,
        "transaction_count": len(year_items),
    }


@router.get("/report/{user_id}/{year}/{month}")
def get_month_report(
    user_id: str,
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")

    month_items = get_all_items_for_month(user_id, year, month, db)

    total_money_in, total_money_out, net_flow = calculate_money_summary(month_items)

    today = date.today()
    is_ongoing_month = year == today.year and month == today.month
    is_completed_month = (year < today.year) or (
        year == today.year and month < today.month
    )

    return {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "is_completed_month": is_completed_month,
        "is_ongoing_month": is_ongoing_month,
        "summary_label": "" if is_completed_month else "So far....",
        "total_money_in": total_money_in,
        "total_money_out": total_money_out,
        "net_flow": net_flow,
        "week_ranges": get_week_ranges_for_month(year, month),
        "transaction_count": len(month_items),
    }


@router.get("/report/{user_id}/{year}/{month}/{week}")
def get_week_report(
    user_id: str,
    year: int,
    month: int,
    week: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")

    week_range = get_week_range(year, month, week)
    if not week_range:
        raise HTTPException(status_code=400, detail="Invalid week for this month")

    month_items = get_all_items_for_month(user_id, year, month, db)

    week_items = filter_items_by_week(
        month_items,
        year,
        month,
        week_range["start_day"],
        week_range["end_day"],
    )

    total_money_in, total_money_out, net_flow = calculate_money_summary(week_items)

    today = date.today()
    is_ongoing_week = (
        year == today.year
        and month == today.month
        and week_range["start_day"] <= today.day <= week_range["end_day"]
    )
    is_completed_week = not is_ongoing_week and (
        year < today.year
        or (year == today.year and month < today.month)
        or (
            year == today.year
            and month == today.month
            and week_range["end_day"] < today.day
        )
    )

    week_items = sorted(week_items, key=lambda item: item["date"])

    return {
        "year": year,
        "month": month,
        "month_name": calendar.month_name[month],
        "week": week,
        "week_label": f"Week {week} ({week_range['start_day']} - {week_range['end_day']})",
        "start_day": week_range["start_day"],
        "end_day": week_range["end_day"],
        "is_completed_week": is_completed_week,
        "is_ongoing_week": is_ongoing_week,
        "summary_label": "" if is_completed_week else "So far....",
        "total_money_in": total_money_in,
        "total_money_out": total_money_out,
        "net_flow": net_flow,
        "transaction_count": len(week_items),
        "transactions": week_items,
    }
