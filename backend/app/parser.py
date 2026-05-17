from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from schemas import NoteInput
from auth import get_current_user
from currency_conversion import apply_currency_conversion
import models
from datetime import date, datetime
from typing import Optional
import requests
import json
import re
import os

router = APIRouter()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))

ALLOWED_CATEGORIES = [
    "grocery", "dining", "fuel", "transport", "shopping", "subscription",
    "rent", "utilities", "salary", "gift", "loan", "transfer",
    "health", "entertainment", "other",
]

ALLOWED_SOURCES = [
    "cash", "credit_card", "debit_card", "checking_account",
    "savings_account", "gift_card", "other",
]

ALLOWED_DIRECTIONS = [
    "expense", "income", "transfer", "loan_given",
    "loan_received", "gift_sent", "gift_received",
]

ALLOWED_SUBJECT_QUALITY = ["clear", "possibly_typo", "unclear"]
ALLOWED_RECURRING_FREQUENCIES = [
    "none", "weekly", "biweekly", "monthly", "yearly", "custom_days",
]
ALLOWED_RECURRING_ACTIONS = ["none", "create", "cancel"]
ALLOWED_STATUSES = ["completed", "cancelled", "projected"]


class ParsedNoteOutput(BaseModel):
    raw_text: str
    date: str
    amount: float
    currency: str
    sender: str
    receiver: str
    counterparty: str
    category: str
    transaction_direction: str
    source: str
    origin_type: str
    status: str
    is_recurring: bool
    recurring_frequency: str
    recurring_action: str
    recurring_interval_days: Optional[int] = None
    confidence_score: float
    transaction_subject: str
    subject_quality: str
    missing_fields: list[str]
    ambiguity_reasons: list[str]
    review_level: str

MONEY_WORDS = [
    "usd", "dollar", "dollars", "buck", "bucks",
    "inr", "rupee", "rupees",
    "eur", "euro", "euros",
    "gbp", "pound", "pounds", "quid",
    "cad", "aud", "jpy", "yen", "cny", "yuan", "rub", "aed",
    "chf", "franc", "francs", "swiss", "sfr",
]

NUMBER_PATTERN = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"
CURRENCY_SYMBOL_PATTERN = r"[$₹€£¥]"
MONTH_NAMES = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sept": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def extract_json(text: str):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response")
    return json.loads(match.group(0))


def normalize_string(value, default="unknown"):
    if value is None:
        return default
    value = str(value).strip()
    return value if value else default


def normalize_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def normalize_enum(value, allowed_values, default):
    normalized = normalize_string(value, default).lower()
    return normalized if normalized in allowed_values else default


def normalize_date(value):
    if isinstance(value, date):
        return value.isoformat()

    if value:
        value_text = str(value).strip()
        try:
            return date.fromisoformat(value_text).isoformat()
        except Exception:
            pass

        for date_format in ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"]:
            try:
                return datetime.strptime(value_text, date_format).date().isoformat()
            except Exception:
                pass

    return date.today().isoformat()


def raw_text_has_amount(raw_text: str):
    money_word_pattern = "|".join(re.escape(word) for word in MONEY_WORDS)
    money_patterns = [
        rf"{CURRENCY_SYMBOL_PATTERN}\s*{NUMBER_PATTERN}",
        rf"{NUMBER_PATTERN}\s*{CURRENCY_SYMBOL_PATTERN}",
        rf"\b(?:{money_word_pattern})\s*{NUMBER_PATTERN}\b",
        rf"\b{NUMBER_PATTERN}\s*(?:{money_word_pattern})\b",
    ]

    return any(re.search(pattern, raw_text, re.IGNORECASE) for pattern in money_patterns) or (
        extract_contextual_amount_from_text(raw_text) > 0
    )


def parse_amount_number(value: str):
    return float(str(value).replace(",", ""))


def extract_amount_from_text(raw_text: str):
    money_word_pattern = "|".join(re.escape(word) for word in MONEY_WORDS)
    money_patterns = [
        rf"{CURRENCY_SYMBOL_PATTERN}\s*({NUMBER_PATTERN})",
        rf"\b({NUMBER_PATTERN})\s*{CURRENCY_SYMBOL_PATTERN}",
        rf"\b(?:{money_word_pattern})\s*({NUMBER_PATTERN})\b",
        rf"\b({NUMBER_PATTERN})\s*(?:{money_word_pattern})\b",
    ]

    for pattern in money_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            return parse_amount_number(match.group(1))

    return extract_contextual_amount_from_text(raw_text)


def extract_contextual_amount_from_text(raw_text: str):
    amount_context_patterns = [
        rf"\b(?:paid|pay|spent|spend|cost(?:ed|s)?|charged|billed|owed)\s+(?:about\s+|around\s+)?({NUMBER_PATTERN})\b",
        rf"\b(?:refund|cashback|reimbursement|reimbursed|salary|paycheck|pay)\s+(?:of\s+)?({NUMBER_PATTERN})\b",
        rf"\b(?:pays\s+me|paid\s+me|pay\s+me)\s+(?:about\s+|around\s+)?({NUMBER_PATTERN})\b",
        rf"\b(?:received|receive|earned|got)\s+(?:a\s+|an\s+)?(?:refund|cashback|reimbursement|pay|salary|paycheck)?\s*(?:of\s+)?({NUMBER_PATTERN})\b",
        rf"\b(?:lent|borrowed|transferred|transfer|moved|sent|gave|donated)\s+(?:about\s+|around\s+)?({NUMBER_PATTERN})\b",
        rf"\bfor\s+({NUMBER_PATTERN})\b(?=\s*(?:at|from|to|on|using|with|in|by|$))",
        rf"\bof\s+({NUMBER_PATTERN})\b(?=\s*(?:at|from|to|on|using|with|in|by|$))",
    ]

    for pattern in amount_context_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            return parse_amount_number(match.group(1))

    return 0.0


def raw_text_has_explicit_year(raw_text: str):
    return bool(re.search(r"\b(19|20)\d{2}\b", raw_text))


def extract_explicit_year(raw_text: str):
    match = re.search(r"\b((?:19|20)\d{2})\b", raw_text)
    return int(match.group(1)) if match else None


def strip_ordinal_suffix(value: str):
    return re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", value, flags=re.IGNORECASE)


def extract_date_from_text(raw_text: str):
    text = strip_ordinal_suffix(raw_text)
    current_year = date.today().year

    iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        try:
            return date(
                int(iso_match.group(1)),
                int(iso_match.group(2)),
                int(iso_match.group(3)),
            ).isoformat()
        except ValueError:
            pass

    numeric_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text)
    if numeric_match:
        year = int(numeric_match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(
                year,
                int(numeric_match.group(1)),
                int(numeric_match.group(2)),
            ).isoformat()
        except ValueError:
            pass

    month_pattern = "|".join(MONTH_NAMES)
    month_day_match = re.search(
        rf"\b({month_pattern})\s+(\d{{1,2}})(?:,\s*|\s+)?((?:19|20)\d{{2}})?\b",
        text,
        re.IGNORECASE,
    )
    if month_day_match:
        month = MONTH_NAMES[month_day_match.group(1).lower()]
        day = int(month_day_match.group(2))
        year = int(month_day_match.group(3)) if month_day_match.group(3) else current_year
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            pass

    day_month_match = re.search(
        rf"\b(\d{{1,2}})\s+({month_pattern})(?:,\s*|\s+)?((?:19|20)\d{{2}})?\b",
        text,
        re.IGNORECASE,
    )
    if day_month_match:
        day = int(day_month_match.group(1))
        month = MONTH_NAMES[day_month_match.group(2).lower()]
        year = int(day_month_match.group(3)) if day_month_match.group(3) else current_year
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            pass

    lowered = text.lower()
    if "yesterday" in lowered:
        return date.fromordinal(date.today().toordinal() - 1).isoformat()
    if "tomorrow" in lowered:
        return date.fromordinal(date.today().toordinal() + 1).isoformat()

    return date.today().isoformat()


def add_unique_reason(parsed: dict, field: str, reason: str):
    items = parsed.get(field, [])
    if reason not in items:
        items.append(reason)
    parsed[field] = items


def compact_text(value: str):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def flexible_name_pattern(value: str):
    words = re.findall(r"[a-z0-9]+", str(value).lower())
    if not words:
        return ""

    return r"\s*".join(re.escape(word) for word in words)


def value_is_supported_by_text(value: str, raw_text: str):
    if not value:
        return False

    value = str(value).strip().lower()
    raw_text_lower = raw_text.lower()

    if value in ["me", "unknown", "user"]:
        return True

    if value in raw_text_lower:
        return True

    return compact_text(value) in compact_text(raw_text_lower)


def value_appears_as_location_context(value: str, raw_text: str):
    value_pattern = flexible_name_pattern(value)
    if not value_pattern:
        return False

    location_pattern = (
        rf"\b(?:in|near|around|outside|inside|while\s+in)\s+"
        rf"{value_pattern}\b"
    )
    return bool(re.search(location_pattern, raw_text, re.IGNORECASE))


def value_appears_as_counterparty_context(value: str, raw_text: str):
    value_pattern = flexible_name_pattern(value)
    if not value_pattern:
        return False

    counterparty_patterns = [
        rf"\b(?:at|from|with|to)\s+{value_pattern}\b",
        rf"\b(?:paid|pay|purchased\s+from|bought\s+from|ordered\s+from)\s+{value_pattern}\b",
        rf"\b{value_pattern}\s+(?:charged|billed|paid\s+me|pays\s+me)\b",
    ]

    return any(
        re.search(pattern, raw_text, re.IGNORECASE)
        for pattern in counterparty_patterns
    )


def clean_name(value: str):
    if not value:
        return "unknown"

    value = value.strip()

    remove_phrases = [
        "subscription", "subscriptions", "membership", "memberships",
        "monthly", "weekly", "yearly", "annual", "annually",
        "plan", "payment", "payments", "recurring", "bill", "billing",
        "service", "services", "account", "price", "cost", "fee",
        "premium", "contract",
        "cancel", "cancelled", "canceled", "stopped", "unsubscribe",
        "unsubscribed", "ended", "ends", "terminated", "over",
        "quit", "resigned", "left", "leaving", "job",
        "company", "employer", "work", "working", "started", "today",
        "yesterday", "tomorrow",
        "my", "the", "a", "an", "for", "to", "from", "is", "its", "it's",
        "per", "month", "week", "year",
    ]

    lowered = value.lower()
    for phrase in remove_phrases:
        lowered = re.sub(rf"\b{re.escape(phrase)}\b", "", lowered)

    lowered = re.sub(r"\$?\d+(\.\d+)?", "", lowered)
    lowered = re.sub(r"[^a-zA-Z0-9\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()

    return lowered.title() if lowered else "unknown"


def normalize_extracted_phrase(value: str):
    if not value:
        return "unknown"

    value = strip_ordinal_suffix(str(value))
    value = re.sub(rf"{CURRENCY_SYMBOL_PATTERN}\s*{NUMBER_PATTERN}", " ", value)
    value = re.sub(rf"\b{NUMBER_PATTERN}\s*{CURRENCY_SYMBOL_PATTERN}", " ", value)
    value = re.sub(rf"\b{NUMBER_PATTERN}\s*(?:{'|'.join(re.escape(word) for word in MONEY_WORDS)})\b", " ", value, flags=re.IGNORECASE)
    value = re.sub(rf"\b(?:{'|'.join(re.escape(word) for word in MONEY_WORDS)})\s*{NUMBER_PATTERN}\b", " ", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\b(?:today|yesterday|tomorrow|using|with|on|in|at|from|to|by|cash|credit card|debit card|checking|savings)\b.*$",
        " ",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\b(?:january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|august|aug|september|sept|sep|october|oct|november|nov|december|dec)\s+\d{1,2}(?:,\s*(?:19|20)\d{2})?\b", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", " ", value)
    value = re.sub(r"[^a-zA-Z0-9\s&'-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" -'")

    if not value:
        return "unknown"

    return value


def title_or_unknown(value: str):
    value = normalize_extracted_phrase(value)
    return value if value == "unknown" else value.title()


def extract_name_from_patterns(raw_text: str):
    text = raw_text.strip()

    patterns = [
        r"cancel(?:led|ed)?\s+(?:my\s+)?(.+?)\s+(?:subscription|membership|plan)",
        r"stopped\s+(?:my\s+)?(.+?)\s+(?:subscription|membership|plan)",
        r"stopped\s+using\s+(?:my\s+)?(.+?)(?:\s+today|\s+yesterday|\s+on|\s+last|\s*$)",
        r"unsubscribed\s+from\s+(?:my\s+)?(.+)",
        r"no\s+longer\s+use\s+(?:my\s+)?(.+?)(?:\s+today|\s+yesterday|\s+on|\s+last|\s*$)",
        r"(?:do\s+not|don't)\s+use\s+(?:my\s+)?(.+?)\s+anymore",
        r"(?:my\s+)?contract\s+with\s+(.+?)\s+(?:ended|ends|terminated|is\s+over|was\s+over)",
        r"tenant\s+(.+?)\s+moved\s+out",
        r"(.+?)\s+moved\s+out",
        r"(?:my\s+)?lease\s+with\s+(.+?)\s+(?:ended|ends|terminated|is\s+over|was\s+over)",
        r"quit\s+(?:from|at)\s+(.+?)(?:\s+today|\s+yesterday|\s+on|\s+last|\s*$)",
        r"resigned\s+(?:from|at)\s+(.+?)(?:\s+today|\s+yesterday|\s+on|\s+last|\s*$)",
        r"left\s+(.+?)(?:\s+today|\s+yesterday|\s+on|\s+last|\s*$)",
        r"no\s+longer\s+(?:work|working)\s+(?:for|at)\s+(.+?)(?:\s+today|\s+yesterday|\s+on|\s+last|\s*$)",
        r"last\s+day\s+(?:at|with)\s+(.+?)(?:\s+today|\s+yesterday|\s+on|\s*$)",
        r"(?:my\s+)?(.+?)\s+(?:subscription|membership|plan)\s+(?:started|starts|is|was)",
        r"(?:subscription|membership|plan)\s+(?:to|for)\s+(.+?)(?:\s+started|\s+is|\s+was|$)",
        r"subscribed\s+to\s+(.+?)(?:\s+for|\s+at|\s+today|$)",
        r"salary\s+from\s+(.+?)(?:\s+every|\s+monthly|\s+is|\s+was|$)",
        r"(.+?)\s+pays\s+me",
        r"(.+?)\s+paid\s+me",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = clean_name(match.group(1))
            if name != "unknown":
                return name

    return "unknown"


def get_best_recurring_name(parsed: dict, raw_text: str):
    pattern_name = extract_name_from_patterns(raw_text)
    if pattern_name != "unknown":
        return pattern_name

    for field in ["counterparty", "transaction_subject", "receiver", "sender"]:
        value = parsed.get(field)

        if value and str(value).lower() not in ["unknown", "me", "user"]:
            cleaned = clean_name(str(value))
            if cleaned != "unknown":
                return cleaned

    cleaned = clean_name(raw_text)
    return cleaned


def infer_recurring_frequency(raw_text: str):
    text = raw_text.lower()

    if re.search(r"\b(?:every|each|per)\s+\d+\s+days?\b", text):
        return "custom_days"

    if any(signal in text for signal in ["biweekly", "bi-weekly", "every two weeks", "every 2 weeks", "every other week", "fortnightly", "every fortnight"]):
        return "biweekly"

    if any(signal in text for signal in ["twice a month", "twice monthly", "semi-monthly", "semimonthly"]):
        return "custom_days"

    if any(signal in text for signal in ["weekly", "every week", "per week", "each week"]):
        return "weekly"

    if any(signal in text for signal in ["yearly", "annually", "annual", "every year", "per year", "each year"]):
        return "yearly"

    if any(signal in text for signal in ["monthly", "every month", "per month", "each month"]):
        return "monthly"

    return "none"


def infer_recurring_interval_days(raw_text: str, frequency: str):
    text = raw_text.lower()

    if frequency == "biweekly":
        return 14

    if frequency == "custom_days" and any(
        signal in text
        for signal in ["twice a month", "twice monthly", "semi-monthly", "semimonthly"]
    ):
        return 15

    match = re.search(r"\b(?:every|each|per)\s+(\d+)\s+days?\b", text)
    if match:
        return max(1, int(match.group(1)))

    return None


def premium_is_likely_subscription(raw_text: str):
    text = raw_text.lower()

    if "premium" not in text and not re.search(r"\bpro\b", text):
        return False

    subscription_context = [
        "premium subscription", "premium membership", "premium plan",
        "premium account", "premium service", "premium app",
    ]
    if any(signal in text for signal in subscription_context):
        return True

    if re.search(r"\bpro\b", text) and any(
        signal in text
        for signal in ["purchased", "bought", "subscribed", "subscription", "membership", "plan"]
    ):
        return True

    tangible_context = [
        "premium gas", "premium fuel", "premium petrol", "premium diesel",
        "premium coffee", "premium tea", "premium whiskey", "premium whisky",
        "premium wine", "premium beer", "premium liquor", "premium cereal",
        "premium rice", "premium milk", "premium bread", "premium eggs",
        "premium apple", "premium apples", "premium food", "premium grocery",
        "premium groceries", "premium shirt", "premium shoes", "premium jacket",
    ]
    if any(signal in text for signal in tangible_context):
        return False

    return True


def has_one_time_recurring_blocker(raw_text: str):
    text = raw_text.lower()
    one_time_signals = [
        "one-time", "one time", "single payment", "once", "lifetime",
        "life time", "non recurring", "non-recurring",
    ]

    return any(signal in text for signal in one_time_signals)


def infer_recurring_action(raw_text: str):
    text = raw_text.lower()

    cancel_signals = [
        "cancelled", "canceled", "cancel", "stopped", "ended",
        "unsubscribe", "unsubscribed", "no longer subscribed", "terminated",
        "no longer use", "don't use", "do not use", "stopped using",
        "moved out", "lease ended", "lease terminated",
        "quit", "resigned", "left my job", "left the company",
        "left company", "no longer work", "no longer working",
        "last day at", "last day with",
    ]

    create_signals = [
        "subscription", "subscribed", "membership", "monthly", "weekly",
        "biweekly", "bi-weekly", "fortnightly", "yearly", "annually",
        "every month", "every week", "every two weeks", "every 2 weeks",
        "every other week", "every fortnight", "twice a month",
        "twice monthly", "semi-monthly", "semimonthly",
        "every year", "per month", "per week", "per year", "recurring", "plan",
        "charged every", "billed every", "salary every", "paid every",
        "rent every", "due every", "premium plan", "premium subscription",
        "premium membership",
    ]

    if any(signal in text for signal in cancel_signals):
        return "cancel"

    if has_one_time_recurring_blocker(raw_text):
        return "none"

    if premium_is_likely_subscription(raw_text):
        return "create"

    if re.search(r"\b(?:every|each|per)\s+\d+\s+days?\b", text):
        return "create"

    if any(signal in text for signal in create_signals):
        return "create"

    return "none"


def infer_category_from_text(parsed: dict, raw_text: str):
    text = raw_text.lower()
    premium_subscription_signal = premium_is_likely_subscription(raw_text)

    grocery_signals = [
        "grocery", "groceries", "supermarket", "market", "food",
        "rice", "cereal", "dairy", "milk", "bread", "eggs", "cheese",
        "vegetable", "vegetables", "fruit", "fruits",
    ]
    shopping_signals = [
        "clothes", "clothing", "shirt", "pants", "jeans", "shoes",
        "sneakers", "jacket", "coat", "sweater", "dress", "pair of",
        "leg warmer", "leg warmers", "warmer", "warmers",
    ]
    utility_signals = [
        "electricity", "electric bill", "water bill", "internet bill",
        "internet", "wifi", "wi-fi", "phone bill", "utility", "gas bill",
        "heating bill", "sewer bill",
    ]
    health_signals = [
        "doctor", "hospital", "clinic", "copay", "co-pay", "pharmacy",
        "medicine", "medication", "dentist", "therapy", "therapist",
        "health insurance",
    ]
    transport_signals = [
        "taxi", "cab", "bus", "train", "subway", "metro", "parking",
        "toll", "ride", "rideshare", "ride share", "commute",
    ]

    employment_stop_signal = any(
        signal in text
        for signal in [
            "quit", "resigned", "left my job", "left the company",
            "no longer work", "no longer working", "last day at", "last day with",
            "contract with",
        ]
    )

    if employment_stop_signal:
        parsed["category"] = "salary"
    elif any(signal in text for signal in ["salary", "paycheck", "pay cheque", "job at", "joined the company", "joined company"]):
        parsed["category"] = "salary"
    elif any(signal in text for signal in ["rent"]) or (
        "tenant" in text and any(signal in text for signal in ["pays me", "paid me", "moved out"])
    ):
        parsed["category"] = "rent"
    elif any(signal in text for signal in utility_signals):
        parsed["category"] = "utilities"
    elif premium_subscription_signal or any(signal in text for signal in ["subscription", "subscribed", "membership", "plan"]):
        parsed["category"] = "subscription"
    elif any(signal in text for signal in ["coffee", "tea", "lunch", "dinner", "restaurant", "cafe"]):
        parsed["category"] = "dining"
    elif any(signal in text for signal in ["whiskey", "whisky", "wine", "beer", "liquor"]):
        parsed["category"] = "entertainment"
    elif any(signal in text for signal in grocery_signals):
        parsed["category"] = "grocery"
    elif any(signal in text for signal in shopping_signals):
        parsed["category"] = "shopping"
    elif any(signal in text for signal in health_signals):
        parsed["category"] = "health"
    elif any(signal in text for signal in transport_signals):
        parsed["category"] = "transport"
    elif any(signal in text for signal in ["fuel", "gas", "petrol"]):
        parsed["category"] = "fuel"
    elif any(signal in text for signal in ["loan", "lent", "borrowed"]):
        parsed["category"] = "loan"
    elif any(signal in text for signal in ["gift", "gift card", "donation", "donated"]):
        parsed["category"] = "gift"
    elif any(signal in text for signal in ["transfer", "transferred", "moved money"]):
        parsed["category"] = "transfer"

    return parsed


def infer_direction_from_text(parsed: dict, raw_text: str):
    text = raw_text.lower()

    transfer_signals = [
        "transfer from", "transferred from", "move money from",
        "moved money from", "checking to savings", "savings to checking",
    ]

    loan_given_signals = ["lent", "loaned", "gave loan", "loan to"]
    loan_received_signals = ["borrowed", "received loan", "as a loan from", "loan from"]
    gift_received_signals = ["received gift", "got gift", "gift from", "as a gift from"]
    gift_sent_signals = ["gave gift", "sent gift", "gifted", "as a gift"]

    income_signals = [
        "salary", "paycheck", "pay cheque", "paid to me", "pays me",
        "paid me", "i receive", "i received", "receive every",
        "received money", "income", "earned", "refund", "refunded",
        "cashback", "reimbursed", "rent from tenant", "tenant pays",
        "client pays me", "job at", "joined the company", "joined company",
        "gets deposited", "deposited into my account",
        "deposited to my account", "quit", "resigned", "left my job",
        "left the company", "no longer work", "no longer working",
        "last day at", "last day with",
    ]

    expense_signals = [
        "i paid", "paid for", "i pay", "i spend", "i spent",
        "bought", "purchased", "ordered", "charged", "was charged",
        "billed", "subscription", "membership", "bill", "price is",
        "cost is", "costs", "fee", "payment due", "rent due",
        "per month", "per week", "per year", "monthly plan",
        "annual plan", "yearly plan",
    ]

    if any(signal in text for signal in transfer_signals):
        parsed["transaction_direction"] = "transfer"
        parsed["category"] = "transfer"
        return parsed

    if any(signal in text for signal in loan_given_signals) or (
        "loan" in text and any(signal in text for signal in ["i gave", "gave", "i sent", "sent"])
    ):
        parsed["transaction_direction"] = "loan_given"
        parsed["category"] = "loan"
        return parsed

    if any(signal in text for signal in loan_received_signals) or (
        "loan" in text and any(signal in text for signal in ["i received", "received", "got"])
    ):
        parsed["transaction_direction"] = "loan_received"
        parsed["category"] = "loan"
        return parsed

    if any(signal in text for signal in gift_received_signals) or (
        "gift" in text and any(signal in text for signal in ["i received", "received", "got"])
    ):
        parsed["transaction_direction"] = "gift_received"
        parsed["category"] = "gift"
        return parsed

    if ("donated" in text or "donation" in text) or (
        any(signal in text for signal in gift_sent_signals)
        and any(signal in text for signal in ["i sent", "sent", "gave", "gifted"])
    ):
        parsed["transaction_direction"] = "gift_sent"
        parsed["category"] = "gift"
        return parsed

    if any(signal in text for signal in income_signals):
        parsed["transaction_direction"] = "income"
        return parsed

    if any(signal in text for signal in expense_signals):
        parsed["transaction_direction"] = "expense"
        return parsed

    return parsed


def apply_sender_receiver_rules(parsed: dict, raw_text: str = ""):
    direction = parsed.get("transaction_direction")
    counterparty = parsed.get("counterparty", "unknown")
    subject = parsed.get("transaction_subject", "unknown")

    other_party = counterparty if counterparty != "unknown" else subject

    if direction == "expense":
        parsed["sender"] = "Me"

        # For expenses, receiver should be the merchant/person paid, not the
        # product that was purchased.
        if parsed.get("receiver") in ["unknown", "", None, "Me"]:
            parsed["receiver"] = counterparty if counterparty != "unknown" else "unknown"

    elif direction == "loan_given":
        parsed["sender"] = "Me"

        if parsed.get("receiver") in ["unknown", "", None, "Me"]:
            parsed["receiver"] = other_party

    elif direction == "gift_sent":
        parsed["sender"] = "Me"

        if parsed.get("receiver") in ["unknown", "", None, "Me"]:
            parsed["receiver"] = other_party

    elif direction == "income":
        parsed["receiver"] = "Me"

        # For income, sender is the employer/person/source if known. Do not use
        # the income subject itself, such as "pay", as the sender.
        sender = parsed.get("sender")
        if sender in ["", None, "Me"]:
            parsed["sender"] = "unknown"
        elif sender == "unknown" and counterparty != "unknown":
            parsed["sender"] = counterparty
        elif (
            sender == subject
            and counterparty == "unknown"
            and not value_appears_as_counterparty_context(sender, raw_text)
        ):
            parsed["sender"] = "unknown"

    elif direction == "loan_received":
        parsed["receiver"] = "Me"

        if parsed.get("sender") in ["unknown", "", None, "Me"]:
            parsed["sender"] = other_party

    elif direction == "gift_received":
        parsed["receiver"] = "Me"

        if parsed.get("sender") in ["unknown", "", None, "Me"]:
            parsed["sender"] = other_party

    elif direction == "transfer":
        # For transfers, sender/receiver can both be user's own accounts.
        # Do not force Me rules here.
        pass

    return parsed


def apply_basic_business_rules(parsed: dict, raw_text: str):
    text = raw_text.lower()

    parsed = infer_category_from_text(parsed, raw_text)
    parsed = infer_direction_from_text(parsed, raw_text)

    if "gift card" in text:
        parsed["category"] = "gift"
        parsed["source"] = "gift_card"

    if "credit card" in text:
        parsed["source"] = "credit_card"
    elif "debit card" in text:
        parsed["source"] = "debit_card"
    elif "checking" in text:
        parsed["source"] = "checking_account"
    elif "savings" in text:
        parsed["source"] = "savings_account"
    elif "cash" in text:
        parsed["source"] = "cash"

    return parsed


def detect_recurring_from_text(parsed: dict, raw_text: str):
    recurring_action = infer_recurring_action(raw_text)

    if recurring_action == "none":
        if parsed.get("category") == "subscription" and not has_one_time_recurring_blocker(raw_text):
            recurring_action = "create"
        else:
            parsed["is_recurring"] = bool(parsed.get("is_recurring", False))
            parsed["recurring_action"] = "none"
            parsed["recurring_frequency"] = "none"
            parsed["recurring_interval_days"] = None
            return parsed

    if recurring_action == "none":
        parsed["is_recurring"] = bool(parsed.get("is_recurring", False))
        parsed["recurring_action"] = "none"
        parsed["recurring_frequency"] = "none"
        parsed["recurring_interval_days"] = None
        return parsed

    parsed["is_recurring"] = True
    parsed["recurring_action"] = recurring_action

    if recurring_action == "cancel":
        parsed["recurring_frequency"] = "none"
        parsed["recurring_interval_days"] = None
        parsed["status"] = "cancelled"
    else:
        frequency = infer_recurring_frequency(raw_text)
        parsed["recurring_frequency"] = frequency if frequency != "none" else "monthly"
        parsed["recurring_interval_days"] = infer_recurring_interval_days(
            raw_text,
            parsed["recurring_frequency"],
        )

    recurring_name = get_best_recurring_name(parsed, raw_text)

    if parsed.get("transaction_subject") in [None, "", "unknown"]:
        parsed["transaction_subject"] = recurring_name

    if parsed.get("counterparty") in [None, "", "unknown"]:
        parsed["counterparty"] = recurring_name

    parsed = infer_category_from_text(parsed, raw_text)
    parsed = infer_direction_from_text(parsed, raw_text)
    parsed = apply_sender_receiver_rules(parsed, raw_text)

    return parsed


def compute_confidence_and_review_level(parsed: dict):
    score = 1.0

    missing_fields = set(parsed["missing_fields"])
    ambiguity_reasons = parsed["ambiguity_reasons"]
    subject_quality = parsed["subject_quality"]

    if parsed["recurring_action"] == "cancel":
        if parsed["transaction_subject"] == "unknown" and parsed["counterparty"] == "unknown":
            score -= 0.45

        if score >= 0.6:
            parsed["subject_quality"] = "clear"
            parsed["missing_fields"] = [
                field
                for field in parsed.get("missing_fields", [])
                if field not in ["amount", "sender", "receiver"]
            ]
        parsed["confidence_score"] = round(max(0.0, min(score, 1.0)), 2)
        parsed["review_level"] = "quick" if parsed["confidence_score"] >= 0.6 else "full"
        return parsed

    if parsed["amount"] == 0:
        score -= 0.55

    if parsed["transaction_subject"] == "unknown":
        score -= 0.35

    if subject_quality == "possibly_typo":
        score -= 0.22

    if subject_quality == "unclear":
        score -= 0.40

    if ambiguity_reasons:
        score -= min(0.30, 0.15 * len(ambiguity_reasons))

    if parsed["category"] == "other":
        score -= 0.05

    if parsed["source"] == "other":
        score -= 0.02

    direction = parsed["transaction_direction"]

    if direction == "expense":
        has_counterparty_context = (
            parsed["counterparty"] != "unknown" or parsed["receiver"] != "unknown"
        )
        if not has_counterparty_context and parsed["transaction_subject"] == "unknown":
            score -= 0.18

    elif direction in ["loan_given", "gift_sent"]:
        if parsed["receiver"] == "unknown":
            score -= 0.35
        if parsed["counterparty"] == "unknown":
            score -= 0.30

    elif direction == "income":
        if parsed["transaction_subject"] == "unknown":
            score -= 0.18

    elif direction in ["loan_received", "gift_received"]:
        if parsed["sender"] == "unknown":
            score -= 0.30
        if parsed["counterparty"] == "unknown":
            score -= 0.25

    critical_missing = {
        "amount",
        "transaction_subject",
        "direction",
        "sender",
        "receiver",
        "counterparty",
    }

    for field in missing_fields:
        if field in critical_missing:
            score -= 0.10

    score = max(0.0, min(score, 1.0))
    parsed["confidence_score"] = round(score, 2)

    auto_save_safe = (
        score >= 0.85
        and parsed["subject_quality"] == "clear"
        and not ambiguity_reasons
        and parsed["amount"] > 0
        and parsed["transaction_subject"] != "unknown"
        and parsed["recurring_action"] == "none"
    )

    if parsed["recurring_action"] == "create" and parsed["amount"] == 0:
        parsed["review_level"] = "full"
    elif parsed["recurring_action"] in ["create", "cancel"]:
        parsed["review_level"] = "quick"
    elif auto_save_safe:
        parsed["review_level"] = "none"
    elif score >= 0.60:
        parsed["review_level"] = "quick"
    else:
        parsed["review_level"] = "full"

    return parsed


def enforce_evidence_based_fields(parsed: dict, raw_text: str):
    raw_lower = raw_text.lower()

    source_evidence = {
        "cash": ["cash"],
        "credit_card": ["credit card", "credit-card", "creditcard"],
        "debit_card": ["debit card", "debit-card", "debitcard"],
        "checking_account": ["checking", "checking account"],
        "savings_account": ["savings", "savings account"],
        "gift_card": ["gift card", "gift-card", "giftcard"],
        "other": [],
    }

    source = parsed.get("source", "other")
    if source != "other":
        allowed_terms = source_evidence.get(source, [])
        if not any(term in raw_lower for term in allowed_terms):
            parsed["source"] = "other"

    for field in ["receiver", "counterparty", "sender"]:
        value = parsed.get(field, "unknown")

        if str(value).lower() not in ["me", "unknown"]:
            if not value_is_supported_by_text(value, raw_text):
                parsed[field] = "unknown"

    return parsed


def remove_location_only_counterparties(parsed: dict, raw_text: str):
    for field in ["receiver", "counterparty"]:
        value = parsed.get(field, "unknown")

        if str(value).lower() in ["me", "unknown"]:
            continue

        if (
            value_appears_as_location_context(value, raw_text)
            and not value_appears_as_counterparty_context(value, raw_text)
        ):
            parsed[field] = "unknown"

    return parsed


def has_complete_party_fields(parsed: dict):
    direction = parsed.get("transaction_direction")

    if direction in ["expense", "loan_given", "gift_sent"]:
        if direction == "expense":
            return (
                parsed.get("sender") != "unknown"
                and parsed.get("transaction_subject") != "unknown"
            )

        return (
            parsed.get("sender") != "unknown"
            and parsed.get("receiver") != "unknown"
            and parsed.get("counterparty") != "unknown"
        )

    if direction == "income":
        return (
            parsed.get("receiver") != "unknown"
            and parsed.get("transaction_subject") != "unknown"
        )

    if direction in ["loan_received", "gift_received"]:
        return (
            parsed.get("sender") != "unknown"
            and parsed.get("receiver") != "unknown"
            and parsed.get("counterparty") != "unknown"
        )

    if direction == "transfer":
        return parsed.get("sender") != "unknown" and parsed.get("receiver") != "unknown"

    return False


def subject_is_supported_by_text(parsed: dict, raw_text: str):
    subject = parsed.get("transaction_subject", "unknown")

    if value_is_supported_by_text(subject, raw_text):
        return True

    text = raw_text.lower()
    direction = parsed.get("transaction_direction")
    category = parsed.get("category")
    counterparty = parsed.get("counterparty", "unknown")

    if (
        direction == "income"
        and category == "salary"
        and counterparty != "unknown"
        and value_is_supported_by_text(counterparty, raw_text)
        and any(signal in text for signal in ["salary", "pay", "paid", "paycheck", "job", "wage", "wages"])
    ):
        return True

    if (
        direction == "income"
        and counterparty != "unknown"
        and value_is_supported_by_text(counterparty, raw_text)
        and any(signal in text for signal in ["refund", "cashback", "reimbursement", "reimbursed"])
    ):
        return True

    if (
        direction in ["loan_received", "loan_given"]
        and category == "loan"
        and counterparty != "unknown"
        and value_is_supported_by_text(counterparty, raw_text)
        and "loan" in text
    ):
        return True

    if (
        direction == "income"
        and category == "rent"
        and counterparty != "unknown"
        and value_is_supported_by_text(counterparty, raw_text)
        and any(signal in text for signal in ["rent", "tenant"])
    ):
        return True

    if (
        direction in ["gift_received", "gift_sent"]
        and category == "gift"
        and counterparty != "unknown"
        and value_is_supported_by_text(counterparty, raw_text)
        and any(signal in text for signal in ["gift", "donation", "donated"])
    ):
        return True

    if (
        category == "subscription"
        and counterparty != "unknown"
        and value_is_supported_by_text(counterparty, raw_text)
        and any(signal in text for signal in ["subscription", "membership", "plan"])
    ):
        return True

    return False


def reconcile_subject_quality(parsed: dict, raw_text: str):
    if parsed.get("subject_quality") != "unclear":
        return parsed

    subject = parsed.get("transaction_subject", "unknown")

    if subject == "unknown":
        return parsed

    if parsed.get("amount", 0) <= 0:
        return parsed

    if parsed.get("ambiguity_reasons"):
        return parsed

    critical_missing = {
        "amount",
        "transaction_subject",
        "direction",
        "sender",
        "receiver",
        "counterparty",
    }

    if critical_missing.intersection(set(parsed.get("missing_fields", []))):
        return parsed

    if not subject_is_supported_by_text(parsed, raw_text):
        return parsed

    if not has_complete_party_fields(parsed):
        return parsed

    parsed["subject_quality"] = "clear"
    return parsed


def enforce_amount_evidence(parsed: dict, raw_text: str):
    if parsed.get("amount", 0) <= 0:
        extracted_amount = extract_amount_from_text(raw_text)
        if extracted_amount > 0:
            parsed["amount"] = extracted_amount
        return parsed

    if raw_text_has_amount(raw_text):
        return parsed

    parsed["amount"] = 0.0
    add_unique_reason(parsed, "missing_fields", "amount")
    add_unique_reason(
        parsed,
        "ambiguity_reasons",
        "No money amount was found in the note, so the parsed amount was not trusted.",
    )
    return parsed


def remove_resolved_missing_field(parsed: dict, field_name: str):
    parsed["missing_fields"] = [
        field for field in parsed.get("missing_fields", []) if field != field_name
    ]


def remove_resolved_amount_warning(parsed: dict):
    parsed["ambiguity_reasons"] = [
        reason
        for reason in parsed.get("ambiguity_reasons", [])
        if "No money amount was found" not in reason
    ]


def reconcile_date_year(parsed: dict, raw_text: str):
    try:
        parsed_date = date.fromisoformat(parsed["date"])
    except Exception:
        return parsed

    explicit_year = extract_explicit_year(raw_text)
    target_year = explicit_year or date.today().year
    text = raw_text.lower()

    if explicit_year is None and "last year" in text:
        target_year -= 1
    elif explicit_year is None and "next year" in text:
        target_year += 1

    if parsed_date.year != target_year:
        parsed["date"] = parsed_date.replace(year=target_year).isoformat()

    return parsed


def validate_and_cleanup(parsed: dict, raw_text: str, user_currency: str):
    parsed["raw_text"] = raw_text
    parsed["origin_type"] = "note"

    parsed["category"] = normalize_enum(
        parsed.get("category"),
        ALLOWED_CATEGORIES,
        "other",
    )

    parsed["source"] = normalize_enum(parsed.get("source"), ALLOWED_SOURCES, "other")

    parsed["transaction_direction"] = normalize_enum(
        parsed.get("transaction_direction"),
        ALLOWED_DIRECTIONS,
        "expense",
    )

    try:
        parsed["amount"] = abs(float(parsed.get("amount", 0)))
    except Exception:
        parsed["amount"] = 0.0

    parsed["currency"] = user_currency or "USD"
    parsed["sender"] = normalize_string(parsed.get("sender"))
    parsed["receiver"] = normalize_string(parsed.get("receiver"))
    parsed["counterparty"] = normalize_string(parsed.get("counterparty"))
    parsed["status"] = normalize_enum(parsed.get("status"), ALLOWED_STATUSES, "completed")
    parsed["is_recurring"] = bool(parsed.get("is_recurring", False))

    parsed["recurring_frequency"] = normalize_enum(
        parsed.get("recurring_frequency"),
        ALLOWED_RECURRING_FREQUENCIES,
        "none",
    )

    parsed["recurring_action"] = normalize_enum(
        parsed.get("recurring_action"),
        ALLOWED_RECURRING_ACTIONS,
        "none",
    )

    try:
        interval_days = parsed.get("recurring_interval_days")
        parsed["recurring_interval_days"] = (
            int(interval_days) if interval_days not in [None, "", "none"] else None
        )
    except Exception:
        parsed["recurring_interval_days"] = None

    parsed["date"] = normalize_date(parsed.get("date"))

    parsed["transaction_subject"] = normalize_string(
        parsed.get("transaction_subject"), "unknown"
    )

    parsed["subject_quality"] = normalize_enum(
        parsed.get("subject_quality"),
        ALLOWED_SUBJECT_QUALITY,
        "unclear",
    )

    parsed["missing_fields"] = normalize_list(parsed.get("missing_fields"))
    parsed["ambiguity_reasons"] = normalize_list(parsed.get("ambiguity_reasons"))

    parsed = enforce_evidence_based_fields(parsed, raw_text)
    parsed = remove_location_only_counterparties(parsed, raw_text)
    parsed = enforce_amount_evidence(parsed, raw_text)
    if parsed["amount"] > 0:
        remove_resolved_missing_field(parsed, "amount")
        remove_resolved_amount_warning(parsed)
    parsed = reconcile_date_year(parsed, raw_text)
    parsed = apply_basic_business_rules(parsed, raw_text)
    parsed = detect_recurring_from_text(parsed, raw_text)
    parsed = apply_sender_receiver_rules(parsed, raw_text)
    parsed = remove_location_only_counterparties(parsed, raw_text)
    parsed = reconcile_subject_quality(parsed, raw_text)
    parsed = compute_confidence_and_review_level(parsed)
    parsed = apply_currency_conversion(parsed, raw_text, user_currency)

    return parsed


def first_pattern_value(raw_text: str, patterns):
    for pattern in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            for group in match.groups():
                value = normalize_extracted_phrase(group)
                if value != "unknown":
                    return value
    return "unknown"


def extract_counterparty_from_text(raw_text: str, direction: str):
    if direction == "transfer":
        return "Me"

    patterns = []
    if direction in ["income", "loan_received", "gift_received"]:
        patterns = [
            r"\bfrom\s+(.+?)(?:\s+as\s+|\s+for\s+|\s+on\s+|\s+using\s+|$)",
            r"\bby\s+(.+?)(?:\s+for\s+|\s+on\s+|\s+using\s+|$)",
            r"\b(?:tenant|client)\s+(.+?)\s+(?:paid|pays|sent|gave)\s+me\b",
            r"\b(.+?)\s+(?:paid|pays|sent|gave)\s+me\b",
            r"\bjob\s+at\s+(.+?)(?:,|\s+on\s+|\s+for\s+|\s+every\s+|$)",
            r"\bjoined\s+(.+?)(?:,|\s+on\s+|\s+for\s+|\s+every\s+|$)",
        ]
    elif direction in ["loan_given", "gift_sent"]:
        patterns = [
            r"\bto\s+(.+?)(?:\s+as\s+|\s+for\s+|\s+on\s+|\s+using\s+|$)",
            r"\b(?:lent|loaned|gave|sent|gifted|donated)\s+(?:.+?\s+)?to\s+(.+?)(?:\s+as\s+|\s+for\s+|\s+on\s+|\s+using\s+|$)",
        ]
    else:
        patterns = [
            r"\bat\s+(.+?)(?:\s+for\s+|\s+on\s+|\s+using\s+|\s+with\s+|$)",
            r"\bfrom\s+(.+?)(?:\s+for\s+|\s+on\s+|\s+using\s+|\s+with\s+|$)",
            r"\b(?:paid|pay|bought|purchased|ordered)\s+(?:from\s+)?(.+?)\s+for\s+",
            r"\b(?:charged|billed)\s+by\s+(.+?)(?:\s+for\s+|\s+on\s+|$)",
        ]

    value = first_pattern_value(raw_text, patterns)
    return title_or_unknown(value)


def extract_transfer_accounts(raw_text: str):
    match = re.search(
        r"\b(?:transfer(?:red)?|move(?:d)?)\s+(?:money\s+)?(?:.+?\s+)?from\s+(.+?)\s+to\s+(.+?)(?:\s+on\s+|$)",
        raw_text,
        re.IGNORECASE,
    )
    if not match:
        return "unknown", "unknown"

    return normalize_extracted_phrase(match.group(1)), normalize_extracted_phrase(match.group(2))


def extract_subject_from_text(raw_text: str, direction: str, category: str, counterparty: str):
    text = raw_text.lower()

    if direction == "transfer":
        sender, receiver = extract_transfer_accounts(raw_text)
        if sender != "unknown" and receiver != "unknown":
            return f"{sender} to {receiver}"
        return "transfer"

    if direction == "income":
        if category == "salary":
            return f"pay from {counterparty}" if counterparty != "unknown" else "pay"
        if category == "rent":
            return f"rent from {counterparty}" if counterparty != "unknown" else "rent"
        if "refund" in text:
            return f"refund from {counterparty}" if counterparty != "unknown" else "refund"
        if "cashback" in text:
            return f"cashback from {counterparty}" if counterparty != "unknown" else "cashback"
        if "reimbursement" in text or "reimbursed" in text:
            return f"reimbursement from {counterparty}" if counterparty != "unknown" else "reimbursement"
        return f"income from {counterparty}" if counterparty != "unknown" else "income"

    if direction in ["loan_received", "loan_given"]:
        if counterparty != "unknown":
            return f"loan from {counterparty}" if direction == "loan_received" else f"loan to {counterparty}"
        return "loan"

    if direction in ["gift_received", "gift_sent"]:
        if "donat" in text:
            return "donation"
        if counterparty != "unknown":
            return f"gift from {counterparty}" if direction == "gift_received" else f"gift to {counterparty}"
        return "gift"

    subject_patterns = [
        r"\b(?:bought|purchased|ordered)\s+(.+?)\s+for\s+",
        r"\b(?:paid|spent)\s+(?:.+?\s+)?(?:for|on)\s+(.+?)(?:\s+at\s+|\s+from\s+|\s+on\s+|\s+using\s+|$)",
        r"\bfor\s+(.+?)(?:\s+at\s+|\s+from\s+|\s+on\s+|\s+using\s+|$)",
        r"\b(?:subscription|membership|plan)\s+(?:to|for)\s+(.+?)(?:\s+for\s+|\s+at\s+|\s+on\s+|$)",
        r"\bsubscribed\s+to\s+(.+?)(?:\s+for\s+|\s+at\s+|\s+on\s+|$)",
    ]
    subject = first_pattern_value(raw_text, subject_patterns)

    if subject == "unknown" and counterparty != "unknown" and category == "subscription":
        subject = f"{counterparty} subscription"

    if subject == "unknown":
        return "unknown"

    return subject


def apply_rule_based_party_and_subject_fields(parsed: dict, raw_text: str):
    parsed = apply_basic_business_rules(parsed, raw_text)
    direction = parsed.get("transaction_direction", "expense")
    category = parsed.get("category", "other")

    counterparty = extract_counterparty_from_text(raw_text, direction)
    recurring_name = extract_name_from_patterns(raw_text)
    if counterparty == "unknown" and recurring_name != "unknown":
        counterparty = recurring_name

    if counterparty != "unknown":
        parsed["counterparty"] = counterparty

    subject = extract_subject_from_text(raw_text, direction, category, parsed.get("counterparty", "unknown"))
    if subject != "unknown":
        parsed["transaction_subject"] = subject
        parsed["subject_quality"] = "clear"
        remove_resolved_missing_field(parsed, "transaction_subject")
        parsed["ambiguity_reasons"] = [
            reason
            for reason in parsed.get("ambiguity_reasons", [])
            if "transaction subject" not in reason.lower()
        ]

    if direction == "transfer":
        sender, receiver = extract_transfer_accounts(raw_text)
        parsed["sender"] = sender
        parsed["receiver"] = receiver
    elif direction in ["expense", "loan_given", "gift_sent"]:
        parsed["sender"] = "Me"
        if parsed.get("counterparty") != "unknown":
            parsed["receiver"] = parsed["counterparty"]
    elif direction in ["income", "loan_received", "gift_received"]:
        parsed["receiver"] = "Me"
        if parsed.get("counterparty") != "unknown":
            parsed["sender"] = parsed["counterparty"]

    return parsed


def rule_based_fallback(raw_text: str, user_currency: str):
    amount = extract_amount_from_text(raw_text)

    fallback = {
        "raw_text": raw_text,
        "date": extract_date_from_text(raw_text),
        "amount": amount,
        "currency": user_currency or "USD",
        "sender": "unknown",
        "receiver": "unknown",
        "counterparty": "unknown",
        "category": "other",
        "transaction_direction": "expense",
        "source": "other",
        "origin_type": "note",
        "status": "completed",
        "is_recurring": False,
        "recurring_frequency": "none",
        "recurring_interval_days": None,
        "recurring_action": "none",
        "confidence_score": 0.45,
        "transaction_subject": "unknown",
        "subject_quality": "unclear",
        "missing_fields": ["transaction_subject"],
        "ambiguity_reasons": [
            "Fallback parser could not confidently determine the transaction subject."
        ],
        "review_level": "full",
    }

    fallback = apply_rule_based_party_and_subject_fields(fallback, raw_text)
    fallback = apply_basic_business_rules(fallback, raw_text)
    fallback = detect_recurring_from_text(fallback, raw_text)
    fallback = validate_and_cleanup(fallback, raw_text, user_currency)

    if fallback["recurring_action"] in ["create", "cancel"]:
        fallback["confidence_score"] = 0.70
        fallback["review_level"] = "quick"
        fallback["missing_fields"] = []
        fallback["ambiguity_reasons"] = []
        if fallback["recurring_action"] == "cancel":
            fallback["subject_quality"] = "clear"

    return fallback


def call_ollama(prompt: str):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
        timeout=60,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"Ollama error: {response.text}",
        )

    result = response.json()
    model_output = result.get("response", "")
    return extract_json(model_output)


def call_openai(prompt: str):
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT_SECONDS)
    response = client.responses.parse(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": "Extract exactly one finance transaction from the user note.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        text_format=ParsedNoteOutput,
    )

    return response.output_parsed.model_dump()


def call_llm(prompt: str):
    provider = os.getenv("LLM_PROVIDER", LLM_PROVIDER).strip().lower()

    if provider == "openai":
        return call_openai(prompt)

    if provider == "ollama":
        return call_ollama(prompt)

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")


@router.post("/parse-note")
def parse_note(
    note: NoteInput,
    current_user: models.User = Depends(get_current_user),
):
    user_currency = note.currency or current_user.default_currency or "USD"
    today_str = str(date.today())

    prompt = f"""
You are a finance transaction extraction engine.

Return ONLY valid JSON. No markdown. No explanation.

Use "Me" to represent the logged-in user.

Allowed categories:
{ALLOWED_CATEGORIES}

Allowed sources:
{ALLOWED_SOURCES}

Allowed transaction directions:
{ALLOWED_DIRECTIONS}

Allowed recurring_frequency values:
{ALLOWED_RECURRING_FREQUENCIES}

Allowed recurring_action values:
{ALLOWED_RECURRING_ACTIONS}

Core rules:
- raw_text must be the original user note exactly.
- date must be YYYY-MM-DD.
- If no date is mentioned, use today's date: {today_str}.
- amount must be the original money amount mentioned in the note, not quantity.
- Treat common money words such as bucks, dollars, rupees, euros, pounds, quid, yen, and yuan as currency amount evidence.
- If the note explicitly mentions a currency, currency should be that currency code. If no currency is mentioned, currency must be "{user_currency}".
- Do not convert foreign currency yourself. Return the amount as written; Nilebook will fetch the exchange rate and convert it.
- origin_type must always be "note".
- Do not invent payment source. If no payment source is mentioned, source = "other".
- Use "Me" for the logged-in user.

Recurring rules:
- Recurring status does NOT determine money direction by itself.
- If the note mentions subscription, membership, plan, monthly, weekly, yearly, annually, every month, every week, every year, per month, per week, per year, recurring, salary every month, rent every month, or billed every month, set is_recurring = true.
- If the note mentions biweekly, every two weeks, fortnightly, or every/each/per N days, set is_recurring = true.
- If the recurring payment/income is being started, paid, billed, charged, or described as active, recurring_action = "create".
- If the note says cancelled, canceled, stopped, unsubscribed, ended, terminated, or no longer subscribed, recurring_action = "cancel".
- If the note says the user quit, resigned, left a company/job, no longer works there, or has a last day at an employer, recurring_action = "cancel" for the matching recurring income.
- For cancellation notes, amount can be 0 if no amount is mentioned.
- For monthly recurring items, recurring_frequency = "monthly".
- For weekly recurring items, recurring_frequency = "weekly".
- For biweekly recurring items, recurring_frequency = "biweekly" and recurring_interval_days = 14.
- For every/each/per N days recurring items, recurring_frequency = "custom_days" and recurring_interval_days = N.
- For yearly recurring items, recurring_frequency = "yearly".
- If not recurring, is_recurring = false, recurring_frequency = "none", recurring_action = "none".

Direction rules:
- Subscription cost, membership fee, bill, recurring charge, rent due, paid by Me, charged to Me, price per month, or cost per month -> transaction_direction = "expense".
- Salary, paycheck, income, refund, cashback, reimbursement, tenant pays me, client pays me, paid to Me, or money received by Me -> transaction_direction = "income".
- Transfer between Me's own accounts -> transaction_direction = "transfer".
- Me lent money -> transaction_direction = "loan_given".
- Me borrowed money -> transaction_direction = "loan_received".
- Me received a gift -> transaction_direction = "gift_received".
- Me sent/gave a gift -> transaction_direction = "gift_sent".

Counterparty and subject rules:
- counterparty is the main non-Me party involved.
- transaction_subject is the main thing/service/income source involved.
- A city, state, country, or location phrase such as "in New York" is not a counterparty unless the note clearly says the user paid, bought from, ordered from, or was charged by that place/name.
- For product purchases with no merchant/person mentioned, keep receiver and counterparty as "unknown"; put the product only in transaction_subject.
- For recurring items, use the service, company, employer, tenant, membership, bill, or recurring item name.
- Do not rely on a fixed list of known companies. Extract the name from the note.

Return JSON with exactly these keys:
raw_text, date, amount, currency, sender, receiver, counterparty,
category, transaction_direction, source, origin_type, status,
is_recurring, recurring_frequency, recurring_action,
recurring_interval_days,
confidence_score, transaction_subject, subject_quality,
missing_fields, ambiguity_reasons, review_level

User note:
{note.raw_text}
"""

    try:
        parsed = call_llm(prompt)
        parsed = validate_and_cleanup(parsed, note.raw_text, user_currency)

        return parsed

    except Exception:
        return rule_based_fallback(note.raw_text, user_currency)
