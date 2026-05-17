from sqlalchemy import Column, String, Float, Date, Boolean, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    default_currency = Column(String, nullable=False, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, nullable=False, default=False)
    email_verification_token_hash = Column(String, nullable=True)
    email_verification_expires_at = Column(DateTime, nullable=True)
    password_reset_token_hash = Column(String, nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    raw_text = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    original_amount = Column(Float, nullable=True)
    original_currency = Column(String, nullable=True)
    exchange_rate = Column(Float, nullable=True)
    exchange_rate_date = Column(String, nullable=True)
    exchange_rate_source = Column(String, nullable=True)
    exchange_rate_fetched_at = Column(DateTime, nullable=True)

    sender = Column(String, nullable=True)
    receiver = Column(String, nullable=True)
    counterparty = Column(String, nullable=True)

    category = Column(String, nullable=False)
    transaction_direction = Column(String, nullable=False)
    source = Column(String, nullable=False)
    origin_type = Column(String, nullable=False, default="note")

    status = Column(String, nullable=False, default="completed")
    is_recurring = Column(Boolean, nullable=False, default=False)
    confidence_score = Column(Float, nullable=True)
    review_level = Column(String, nullable=False, default="full")

    transaction_subject = Column(String, default="unknown")
    subject_quality = Column(String, default="clear")
    missing_fields = Column(JSON, default=list)
    ambiguity_reasons = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    original_amount = Column(Float, nullable=True)
    original_currency = Column(String, nullable=True)
    exchange_rate = Column(Float, nullable=True)
    exchange_rate_date = Column(String, nullable=True)
    exchange_rate_source = Column(String, nullable=True)
    exchange_rate_fetched_at = Column(DateTime, nullable=True)

    category = Column(String, nullable=False, default="subscription")
    transaction_direction = Column(String, nullable=False, default="expense")
    source = Column(String, nullable=False, default="other")

    frequency = Column(String, nullable=False, default="monthly")
    interval_days = Column(Integer, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    due_day = Column(String, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    created_from_transaction_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
