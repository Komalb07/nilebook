from dataclasses import dataclass
from datetime import date, datetime
import os
import re

import requests


SUPPORTED_CURRENCIES = {
    "USD", "INR", "EUR", "GBP", "CAD",
    "AUD", "JPY", "CNY", "RUB", "AED", "CHF",
}

DOLLAR_CURRENCIES = {"USD", "CAD", "AUD"}
NUMBER_PATTERN = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"

CURRENCY_TERMS = [
    "u.s. dollars",
    "us dollars",
    "american dollars",
    "canadian dollars",
    "australian dollars",
    "dollars",
    "dollar",
    "bucks",
    "buck",
    "rupees",
    "rupee",
    "rs",
    "euros",
    "euro",
    "pounds",
    "pound",
    "quid",
    "yen",
    "yuan",
    "rubles",
    "ruble",
    "dirhams",
    "dirham",
    "swiss francs",
    "swiss franc",
    "francs",
    "franc",
    "sfr",
    "fr",
    "usd",
    "inr",
    "eur",
    "gbp",
    "cad",
    "aud",
    "jpy",
    "cny",
    "rub",
    "aed",
    "chf",
    "$",
    "₹",
    "€",
    "£",
    "¥",
]

CURRENCY_TOKEN_PATTERN = "|".join(
    re.escape(term) for term in sorted(CURRENCY_TERMS, key=len, reverse=True)
)


@dataclass
class ExchangeRateResult:
    rate: float
    rate_date: str
    source: str
    fetched_at: datetime


def normalize_currency_code(value: str):
    code = str(value or "").strip().upper()
    return code if code in SUPPORTED_CURRENCIES else "USD"


def resolve_currency_token(token: str, user_currency: str):
    normalized = re.sub(r"\s+", " ", str(token or "").strip().lower())
    default_currency = normalize_currency_code(user_currency)

    explicit_codes = {
        "usd": "USD",
        "inr": "INR",
        "eur": "EUR",
        "gbp": "GBP",
        "cad": "CAD",
        "aud": "AUD",
        "jpy": "JPY",
        "cny": "CNY",
        "rub": "RUB",
        "aed": "AED",
        "chf": "CHF",
    }

    if normalized in explicit_codes:
        return explicit_codes[normalized]

    if normalized in {"u.s. dollars", "us dollars", "american dollars"}:
        return "USD"

    if normalized == "canadian dollars":
        return "CAD"

    if normalized == "australian dollars":
        return "AUD"

    if normalized in {"$", "dollar", "dollars", "buck", "bucks"}:
        return default_currency if default_currency in DOLLAR_CURRENCIES else "USD"

    if normalized in {"₹", "rs", "rupee", "rupees"}:
        return "INR"

    if normalized in {"€", "euro", "euros"}:
        return "EUR"

    if normalized in {"£", "pound", "pounds", "quid"}:
        return "GBP"

    if normalized in {"yuan"}:
        return "CNY"

    if normalized == "¥":
        return "CNY" if default_currency == "CNY" else "JPY"

    if normalized == "yen":
        return "JPY"

    if normalized in {"ruble", "rubles"}:
        return "RUB"

    if normalized in {"dirham", "dirhams"}:
        return "AED"

    if normalized in {"swiss franc", "swiss francs", "franc", "francs", "sfr", "fr"}:
        return "CHF"

    return default_currency


def detect_transaction_currency(raw_text: str, user_currency: str):
    default_currency = normalize_currency_code(user_currency)
    text = str(raw_text or "")

    patterns = [
        rf"(?P<currency>{CURRENCY_TOKEN_PATTERN})\s*(?:about\s+|around\s+)?{NUMBER_PATTERN}",
        rf"{NUMBER_PATTERN}\s*(?:in\s+|as\s+|worth\s+of\s+)?(?P<currency>{CURRENCY_TOKEN_PATTERN})",
    ]

    mentions = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            code = resolve_currency_token(match.group("currency"), default_currency)
            mentions.append((match.start(), code))

    if not mentions:
        return default_currency

    mentions.sort(key=lambda item: item[0])
    return mentions[0][1]


def normalize_exchange_rate_date(value):
    if not value:
        return date.today().isoformat()

    value_text = str(value)
    iso_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", value_text)
    if iso_match:
        return iso_match.group(0)

    return date.today().isoformat()


def fetch_exchange_rate(from_currency: str, to_currency: str):
    from_currency = normalize_currency_code(from_currency)
    to_currency = normalize_currency_code(to_currency)

    if from_currency == to_currency:
        return ExchangeRateResult(
            rate=1.0,
            rate_date=date.today().isoformat(),
            source="same_currency",
            fetched_at=datetime.utcnow(),
        )

    api_url = os.getenv(
        "EXCHANGE_RATE_API_URL",
        "https://open.er-api.com/v6/latest/{base}",
    )
    timeout_seconds = float(os.getenv("EXCHANGE_RATE_TIMEOUT_SECONDS", "8"))
    url = api_url.format(base=from_currency, target=to_currency)

    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()

    rates = payload.get("rates") or payload.get("conversion_rates") or {}
    if to_currency not in rates:
        raise ValueError(f"No exchange rate found for {from_currency} to {to_currency}")

    source_name = os.getenv("EXCHANGE_RATE_SOURCE_NAME", "open.er-api.com")
    rate_date = normalize_exchange_rate_date(
        payload.get("date") or payload.get("time_last_update_utc")
    )

    return ExchangeRateResult(
        rate=float(rates[to_currency]),
        rate_date=rate_date,
        source=source_name,
        fetched_at=datetime.utcnow(),
    )


def add_conversion_reason(parsed: dict, reason: str):
    reasons = parsed.get("ambiguity_reasons", [])
    if reason not in reasons:
        reasons.append(reason)
    parsed["ambiguity_reasons"] = reasons


def initialize_conversion_fields(parsed: dict):
    parsed["original_amount"] = parsed.get("original_amount")
    parsed["original_currency"] = parsed.get("original_currency")
    parsed["converted_amount"] = parsed.get("converted_amount")
    parsed["converted_currency"] = parsed.get("converted_currency")
    parsed["exchange_rate"] = parsed.get("exchange_rate")
    parsed["exchange_rate_date"] = parsed.get("exchange_rate_date")
    parsed["exchange_rate_source"] = parsed.get("exchange_rate_source")
    parsed["exchange_rate_fetched_at"] = parsed.get("exchange_rate_fetched_at")
    parsed["requires_conversion_confirmation"] = bool(
        parsed.get("requires_conversion_confirmation", False)
    )
    parsed["conversion_error"] = parsed.get("conversion_error")


def apply_currency_conversion(
    parsed: dict,
    raw_text: str,
    user_currency: str,
    rate_fetcher=fetch_exchange_rate,
):
    initialize_conversion_fields(parsed)

    default_currency = normalize_currency_code(user_currency)
    parsed["currency"] = default_currency

    note_currency = detect_transaction_currency(raw_text, default_currency)
    if note_currency == default_currency:
        return parsed

    try:
        original_amount = abs(float(parsed.get("amount", 0) or 0))
    except Exception:
        original_amount = 0.0

    parsed["original_amount"] = original_amount if original_amount > 0 else None
    parsed["original_currency"] = note_currency
    parsed["converted_currency"] = default_currency

    if original_amount <= 0:
        return parsed

    try:
        rate_result = rate_fetcher(note_currency, default_currency)
        converted_amount = round(original_amount * rate_result.rate, 2)
    except Exception:
        parsed["currency"] = note_currency
        parsed["conversion_error"] = (
            f"Could not fetch exchange rate for {note_currency} to {default_currency}."
        )
        parsed["requires_conversion_confirmation"] = False
        parsed["review_level"] = "full"
        missing_fields = parsed.get("missing_fields", [])
        if "exchange_rate" not in missing_fields:
            missing_fields.append("exchange_rate")
        parsed["missing_fields"] = missing_fields
        add_conversion_reason(parsed, parsed["conversion_error"])
        return parsed

    parsed["amount"] = converted_amount
    parsed["currency"] = default_currency
    parsed["converted_amount"] = converted_amount
    parsed["exchange_rate"] = rate_result.rate
    parsed["exchange_rate_date"] = rate_result.rate_date
    parsed["exchange_rate_source"] = rate_result.source
    parsed["exchange_rate_fetched_at"] = rate_result.fetched_at.isoformat()
    parsed["requires_conversion_confirmation"] = True
    parsed["conversion_error"] = None

    if parsed.get("review_level") == "none":
        parsed["review_level"] = "quick"

    return parsed
