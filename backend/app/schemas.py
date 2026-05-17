from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime


class NoteInput(BaseModel):
    raw_text: str
    currency: str = "USD"


class ParsedTransaction(BaseModel):
    raw_text: str
    date: date
    amount: float
    currency: str
    original_amount: Optional[float] = None
    original_currency: Optional[str] = None
    converted_amount: Optional[float] = None
    converted_currency: Optional[str] = None
    exchange_rate: Optional[float] = None
    exchange_rate_date: Optional[str] = None
    exchange_rate_source: Optional[str] = None
    exchange_rate_fetched_at: Optional[datetime] = None
    requires_conversion_confirmation: bool = False
    conversion_error: Optional[str] = None
    sender: str
    receiver: str
    counterparty: str
    category: str
    transaction_direction: str
    source: str
    origin_type: str
    status: str
    is_recurring: bool
    confidence_score: float
    subject_quality: str
    review_level: str
    transaction_subject: str = "unknown"
    missing_fields: List[str] = Field(default_factory=list)
    ambiguity_reasons: List[str] = Field(default_factory=list)
    recurring_frequency: Optional[str] = "none"
    recurring_interval_days: Optional[int] = None
    recurring_action: Optional[str] = "none"


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    default_currency: str = "USD"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    first_name: str
    last_name: str
    email: EmailStr
    default_currency: str


class TransactionCreate(ParsedTransaction):
    user_id: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class DeleteAccountRequest(BaseModel):
    password: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class RecurringTransactionCreate(BaseModel):
    user_id: str
    name: str
    amount: float
    currency: str = "USD"
    original_amount: Optional[float] = None
    original_currency: Optional[str] = None
    exchange_rate: Optional[float] = None
    exchange_rate_date: Optional[str] = None
    exchange_rate_source: Optional[str] = None
    exchange_rate_fetched_at: Optional[datetime] = None
    category: str = "subscription"
    transaction_direction: str = "expense"
    source: str = "other"
    frequency: str = "monthly"
    interval_days: Optional[int] = None
    start_date: date
    due_day: Optional[str] = None
    created_from_transaction_id: Optional[str] = None


class RecurringTransactionCancel(BaseModel):
    user_id: str
    name: str
    cancel_date: date


class RecurringTransactionConfirmCancel(BaseModel):
    user_id: str
    cancel_date: date


class RecurringTransactionResponse(BaseModel):
    id: str
    user_id: str
    name: str
    amount: float
    currency: str
    original_amount: Optional[float]
    original_currency: Optional[str]
    exchange_rate: Optional[float]
    exchange_rate_date: Optional[str]
    exchange_rate_source: Optional[str]
    exchange_rate_fetched_at: Optional[datetime]
    category: str
    transaction_direction: str
    source: str
    frequency: str
    interval_days: Optional[int]
    start_date: date
    end_date: Optional[date]
    due_day: Optional[str]
    is_active: bool
    created_from_transaction_id: Optional[str]

    class Config:
        from_attributes = True
