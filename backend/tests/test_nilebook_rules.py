import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

import models  # noqa: E402
import parser  # noqa: E402
from currency_conversion import (  # noqa: E402
    ExchangeRateResult,
    apply_currency_conversion,
    detect_transaction_currency,
)
from parser import rule_based_fallback, validate_and_cleanup  # noqa: E402
from recurring import find_best_recurring_match  # noqa: E402
from report import get_recurring_occurrence_dates, recurring_to_dict  # noqa: E402
from transactions import delete_transaction  # noqa: E402
from users import update_currency  # noqa: E402


def base_model_output(note, **overrides):
    data = {
        "raw_text": note,
        "date": date.today().isoformat(),
        "amount": 0,
        "currency": "USD",
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
        "confidence_score": 0,
        "transaction_subject": "unknown",
        "subject_quality": "unclear",
        "missing_fields": [],
        "ambiguity_reasons": [],
        "review_level": "full",
    }
    data.update(overrides)
    return data


def without_currency_conversion(parsed, raw_text, user_currency):
    return parsed


def cleaned(note, user_currency="USD", **overrides):
    original_converter = parser.apply_currency_conversion
    parser.apply_currency_conversion = without_currency_conversion
    try:
        return validate_and_cleanup(
            base_model_output(note, **overrides),
            note,
            user_currency,
        )
    finally:
        parser.apply_currency_conversion = original_converter


def fallback_without_conversion(note, user_currency="USD"):
    original_converter = parser.apply_currency_conversion
    parser.apply_currency_conversion = without_currency_conversion
    try:
        return rule_based_fallback(note, user_currency)
    finally:
        parser.apply_currency_conversion = original_converter


def fallback_with_fake_conversion(note, user_currency="USD", rate=1.1):
    def fake_fetcher(from_currency, to_currency):
        return ExchangeRateResult(
            rate=rate,
            rate_date="2026-05-16",
            source="unit-test",
            fetched_at=datetime(2026, 5, 16, 12, 0, 0),
        )

    def fake_converter(parsed, raw_text, selected_currency):
        return apply_currency_conversion(
            parsed,
            raw_text,
            selected_currency,
            rate_fetcher=fake_fetcher,
        )

    original_converter = parser.apply_currency_conversion
    parser.apply_currency_conversion = fake_converter
    try:
        return parser.rule_based_fallback(note, user_currency)
    finally:
        parser.apply_currency_conversion = original_converter


def cleaned_with_fake_conversion(note, user_currency="USD", rate=1.1, **overrides):
    def fake_fetcher(from_currency, to_currency):
        return ExchangeRateResult(
            rate=rate,
            rate_date="2026-05-16",
            source="unit-test",
            fetched_at=datetime(2026, 5, 16, 12, 0, 0),
        )

    def fake_converter(parsed, raw_text, selected_currency):
        return apply_currency_conversion(
            parsed,
            raw_text,
            selected_currency,
            rate_fetcher=fake_fetcher,
        )

    original_converter = parser.apply_currency_conversion
    parser.apply_currency_conversion = fake_converter
    try:
        return validate_and_cleanup(
            base_model_output(note, **overrides),
            note,
            user_currency,
        )
    finally:
        parser.apply_currency_conversion = original_converter


class ParserRuleTests(unittest.TestCase):
    def assert_subset(self, actual, expected):
        for key, value in expected.items():
            self.assertEqual(actual.get(key), value, f"{key}: {actual}")

    def test_expense_notes_with_money_words_and_location_context(self):
        cases = [
            (
                "I had to buy a pair of leg warmers in order to tackle the cold weather in Newyork which costed me 46 bucks.",
                {
                    "amount": 46.0,
                    "category": "shopping",
                    "transaction_direction": "expense",
                    "receiver": "unknown",
                    "counterparty": "unknown",
                    "transaction_subject": "leg warmers",
                    "subject_quality": "clear",
                    "review_level": "none",
                },
                {
                    "amount": 0,
                    "receiver": "Newyork",
                    "counterparty": "Newyork",
                    "category": "grocery",
                    "transaction_subject": "leg warmers",
                    "missing_fields": ["amount"],
                    "ambiguity_reasons": [
                        "No money amount was found in the note, so the parsed amount was not trusted."
                    ],
                },
            ),
            (
                "I bought milk and eggs for 18 bucks at Natural Dairy.",
                {
                    "amount": 18.0,
                    "category": "grocery",
                    "transaction_direction": "expense",
                    "receiver": "Natural Dairy",
                    "counterparty": "Natural Dairy",
                    "transaction_subject": "milk and eggs",
                    "subject_quality": "clear",
                    "review_level": "none",
                },
                {
                    "amount": 0,
                    "receiver": "Natural Dairy",
                    "counterparty": "Natural Dairy",
                    "transaction_subject": "milk and eggs",
                    "missing_fields": ["amount"],
                },
            ),
            (
                "I paid 46 at Costco for cereal",
                {
                    "amount": 46.0,
                    "category": "grocery",
                    "transaction_direction": "expense",
                    "receiver": "Costco",
                    "counterparty": "Costco",
                    "transaction_subject": "cereal",
                    "subject_quality": "clear",
                    "review_level": "none",
                },
                {
                    "amount": 46,
                    "receiver": "Costco",
                    "counterparty": "Costco",
                    "transaction_subject": "cereal",
                },
            ),
            (
                "I bought 2 apples for 5 at Costco",
                {
                    "amount": 5.0,
                    "transaction_direction": "expense",
                    "receiver": "Costco",
                    "counterparty": "Costco",
                    "transaction_subject": "apples",
                    "subject_quality": "clear",
                    "review_level": "none",
                },
                {
                    "amount": 5,
                    "receiver": "Costco",
                    "counterparty": "Costco",
                    "transaction_subject": "apples",
                },
            ),
            (
                "Purchased Glenlivet whiskey for 56$ on April 5th 2024.",
                {
                    "amount": 56.0,
                    "date": "2024-04-05",
                    "transaction_direction": "expense",
                    "transaction_subject": "Glenlivet whiskey",
                    "subject_quality": "clear",
                    "review_level": "none",
                },
                {
                    "date": "2026-04-05",
                    "amount": 56,
                    "transaction_subject": "Glenlivet whiskey",
                },
            ),
            (
                "I bought premium whiskey for 56$",
                {
                    "amount": 56.0,
                    "category": "entertainment",
                    "transaction_direction": "expense",
                    "transaction_subject": "premium whiskey",
                    "recurring_action": "none",
                    "review_level": "none",
                },
                {
                    "amount": 56,
                    "category": "entertainment",
                    "transaction_subject": "premium whiskey",
                },
            ),
            (
                "I bought a premium coffee for 6 bucks",
                {
                    "amount": 6.0,
                    "category": "dining",
                    "transaction_direction": "expense",
                    "transaction_subject": "premium coffee",
                    "recurring_action": "none",
                    "review_level": "none",
                },
                {
                    "amount": 6,
                    "transaction_subject": "premium coffee",
                },
            ),
            (
                "I bought a lifetime membership to Museum of Art for 100$",
                {
                    "amount": 100.0,
                    "category": "subscription",
                    "transaction_direction": "expense",
                    "counterparty": "Museum of Art",
                    "transaction_subject": "Museum of Art membership",
                    "recurring_action": "none",
                    "review_level": "none",
                },
                {
                    "amount": 100,
                    "receiver": "Museum of Art",
                    "counterparty": "Museum of Art",
                    "transaction_subject": "Museum of Art membership",
                },
            ),
        ]

        for note, expected, overrides in cases:
            with self.subTest(note=note):
                self.assert_subset(cleaned(note, **overrides), expected)

    def test_income_notes_do_not_require_named_sender(self):
        cases = [
            (
                "I received a pay of 240$",
                {
                    "amount": 240.0,
                    "category": "salary",
                    "transaction_direction": "income",
                    "sender": "unknown",
                    "receiver": "Me",
                    "transaction_subject": "pay",
                    "subject_quality": "clear",
                    "review_level": "none",
                },
                {
                    "amount": 240,
                    "sender": "pay",
                    "receiver": "Me",
                    "counterparty": "unknown",
                    "category": "salary",
                    "transaction_direction": "income",
                    "transaction_subject": "pay",
                },
            ),
            (
                "Joey paid me 50$",
                {
                    "amount": 50.0,
                    "transaction_direction": "income",
                    "sender": "Joey",
                    "receiver": "Me",
                    "subject_quality": "clear",
                    "review_level": "none",
                },
                {
                    "amount": 50,
                    "sender": "Joey",
                    "receiver": "Me",
                    "transaction_direction": "income",
                    "transaction_subject": "Joey",
                },
            ),
            (
                "I got a 30 dollar cashback from Discover.",
                {
                    "amount": 30.0,
                    "transaction_direction": "income",
                    "receiver": "Me",
                    "counterparty": "Discover",
                    "review_level": "none",
                },
                {
                    "amount": 30,
                    "sender": "Discover",
                    "receiver": "Me",
                    "counterparty": "Discover",
                    "transaction_direction": "income",
                    "transaction_subject": "cashback from Discover",
                },
            ),
            (
                "Got a refund of 45 from Amazon",
                {
                    "amount": 45.0,
                    "transaction_direction": "income",
                    "sender": "Amazon",
                    "receiver": "Me",
                    "counterparty": "Amazon",
                    "subject_quality": "clear",
                    "review_level": "none",
                },
                {
                    "amount": 45,
                    "sender": "Amazon",
                    "receiver": "Me",
                    "counterparty": "Amazon",
                    "transaction_direction": "income",
                    "transaction_subject": "refund from Amazon",
                },
            ),
            (
                "I received a pay of $1,650 from Qualitest",
                {
                    "amount": 1650.0,
                    "transaction_direction": "income",
                    "sender": "Qualitest",
                    "receiver": "Me",
                    "counterparty": "Qualitest",
                    "subject_quality": "clear",
                    "review_level": "none",
                },
                {
                    "amount": 1650,
                    "sender": "Qualitest",
                    "receiver": "Me",
                    "counterparty": "Qualitest",
                    "category": "salary",
                    "transaction_direction": "income",
                    "transaction_subject": "pay from Qualitest",
                },
            ),
        ]

        for note, expected, overrides in cases:
            with self.subTest(note=note):
                self.assert_subset(cleaned(note, **overrides), expected)

    def test_recurring_creation_notes(self):
        cases = [
            (
                "I got a job at Qualitest, I joined the company on March 1st. For every 15 days I receive a pay of 1650$",
                {
                    "amount": 1650.0,
                    "date": "2026-03-01",
                    "category": "salary",
                    "transaction_direction": "income",
                    "counterparty": "Qualitest",
                    "recurring_action": "create",
                    "recurring_frequency": "custom_days",
                    "recurring_interval_days": 15,
                    "subject_quality": "clear",
                    "review_level": "quick",
                },
                {
                    "date": "2026-03-01",
                    "amount": 1650,
                    "sender": "Qualitest",
                    "receiver": "Me",
                    "counterparty": "Qualitest",
                    "category": "salary",
                    "transaction_direction": "income",
                    "transaction_subject": "salary from Qualitest",
                    "is_recurring": True,
                },
            ),
            (
                "I get paid biweekly by Acme for 1200$",
                {
                    "amount": 1200.0,
                    "category": "salary",
                    "transaction_direction": "income",
                    "counterparty": "Acme",
                    "recurring_action": "create",
                    "recurring_frequency": "biweekly",
                    "recurring_interval_days": 14,
                    "subject_quality": "clear",
                    "review_level": "quick",
                },
                {
                    "amount": 1200,
                    "sender": "Acme",
                    "receiver": "Me",
                    "counterparty": "Acme",
                    "category": "salary",
                    "transaction_direction": "income",
                    "transaction_subject": "salary from Acme",
                    "is_recurring": True,
                },
            ),
            (
                "I get paid every other week by Acme for 1200$",
                {
                    "amount": 1200.0,
                    "category": "salary",
                    "transaction_direction": "income",
                    "counterparty": "Acme",
                    "recurring_action": "create",
                    "recurring_frequency": "biweekly",
                    "recurring_interval_days": 14,
                    "subject_quality": "clear",
                    "review_level": "quick",
                },
                {
                    "amount": 1200,
                    "sender": "Acme",
                    "receiver": "Me",
                    "counterparty": "Acme",
                    "category": "salary",
                    "transaction_direction": "income",
                    "transaction_subject": "salary from Acme",
                    "is_recurring": True,
                },
            ),
            (
                "Acme pays me 1200$ twice a month",
                {
                    "amount": 1200.0,
                    "category": "salary",
                    "transaction_direction": "income",
                    "counterparty": "Acme",
                    "recurring_action": "create",
                    "recurring_frequency": "custom_days",
                    "recurring_interval_days": 15,
                    "subject_quality": "clear",
                    "review_level": "quick",
                },
                {
                    "amount": 1200,
                    "sender": "Acme",
                    "receiver": "Me",
                    "counterparty": "Acme",
                    "category": "salary",
                    "transaction_direction": "income",
                    "transaction_subject": "salary from Acme",
                    "is_recurring": True,
                },
            ),
            (
                "I purchased Zomato pro on July 15th 1984 for 7$",
                {
                    "amount": 7.0,
                    "date": "1984-07-15",
                    "category": "subscription",
                    "transaction_direction": "expense",
                    "counterparty": "Zomato",
                    "recurring_action": "create",
                    "recurring_frequency": "monthly",
                    "review_level": "quick",
                },
                {
                    "date": "2026-07-15",
                    "amount": 7,
                    "sender": "Me",
                    "receiver": "Zomato",
                    "counterparty": "Zomato",
                    "category": "subscription",
                    "transaction_direction": "expense",
                    "transaction_subject": "Zomato pro",
                    "is_recurring": True,
                },
            ),
        ]

        for note, expected, overrides in cases:
            with self.subTest(note=note):
                self.assert_subset(cleaned(note, **overrides), expected)

    def test_recurring_cancellation_notes_without_amount(self):
        cases = [
            "I quit from Qualitest today",
            "I resigned from Qualitest today",
            "I no longer work at Qualitest",
            "My last day at Qualitest is today",
            "I cancelled my Zee5 premium subscription today",
            "I unsubscribed from Zomato pro",
            "I no longer use Netflix",
            "My contract with Acme ended today",
            "Tenant Bob moved out today",
        ]

        for note in cases:
            with self.subTest(note=note):
                result = cleaned(
                    note,
                    sender="unknown",
                    receiver="unknown",
                    counterparty="unknown",
                    transaction_subject="unknown",
                    missing_fields=["amount", "sender", "receiver"],
                )
                self.assertEqual(result["recurring_action"], "cancel", result)
                self.assertEqual(result["is_recurring"], True, result)
                self.assertEqual(result["status"], "cancelled", result)
                self.assertEqual(result["amount"], 0.0, result)
                self.assertEqual(result["subject_quality"], "clear", result)
                self.assertEqual(result["review_level"], "quick", result)
                self.assertEqual(result["missing_fields"], [], result)

    def test_category_and_direction_edge_cases(self):
        cases = [
            (
                "Paid 80 for my gas bill",
                {"amount": 80.0, "category": "utilities", "transaction_direction": "expense", "review_level": "none"},
                {"amount": 80, "transaction_subject": "gas bill"},
            ),
            (
                "Paid 60 for internet",
                {"amount": 60.0, "category": "utilities", "transaction_direction": "expense", "review_level": "none"},
                {"amount": 60, "transaction_subject": "internet"},
            ),
            (
                "Paid 30 copay at the doctor",
                {"amount": 30.0, "category": "health", "transaction_direction": "expense", "review_level": "none"},
                {"amount": 30, "receiver": "doctor", "counterparty": "doctor", "transaction_subject": "copay"},
            ),
            (
                "Spent 22 on a taxi ride downtown",
                {"amount": 22.0, "category": "transport", "transaction_direction": "expense", "review_level": "none"},
                {"amount": 22, "receiver": "taxi", "counterparty": "taxi", "transaction_subject": "taxi ride"},
            ),
            (
                "I received 200 from Mom as a gift",
                {"amount": 200.0, "category": "gift", "transaction_direction": "gift_received", "subject_quality": "clear", "review_level": "none"},
                {"amount": 200, "sender": "Mom", "receiver": "Me", "counterparty": "Mom", "transaction_subject": "gift from Mom"},
            ),
            (
                "I sent 75 to Priya as a gift",
                {"amount": 75.0, "category": "gift", "transaction_direction": "gift_sent", "subject_quality": "clear", "review_level": "none"},
                {"amount": 75, "sender": "Me", "receiver": "Priya", "counterparty": "Priya", "transaction_subject": "gift to Priya"},
            ),
            (
                "Transferred 500 from checking to savings",
                {"amount": 500.0, "category": "transfer", "transaction_direction": "transfer", "subject_quality": "clear", "review_level": "none"},
                {"amount": 500, "sender": "checking", "receiver": "savings", "transaction_subject": "checking to savings"},
            ),
            (
                "I received 500 as a loan from Alex",
                {"amount": 500.0, "category": "loan", "transaction_direction": "loan_received", "subject_quality": "clear", "review_level": "none"},
                {"amount": 500, "sender": "Alex", "receiver": "Me", "counterparty": "Alex", "transaction_subject": "loan from Alex"},
            ),
            (
                "I gave Alex a loan of 250",
                {"amount": 250.0, "category": "loan", "transaction_direction": "loan_given", "subject_quality": "clear", "review_level": "none"},
                {"amount": 250, "sender": "Me", "receiver": "Alex", "counterparty": "Alex", "transaction_subject": "loan to Alex"},
            ),
            (
                "I donated 20 to Red Cross",
                {"amount": 20.0, "category": "gift", "transaction_direction": "gift_sent", "subject_quality": "clear", "review_level": "none"},
                {"amount": 20, "sender": "Me", "receiver": "Red Cross", "counterparty": "Red Cross", "transaction_subject": "donation"},
            ),
            (
                "I received rent of 1200 from tenant Bob",
                {"amount": 1200.0, "category": "rent", "transaction_direction": "income", "subject_quality": "clear", "review_level": "none"},
                {"amount": 1200, "sender": "Bob", "receiver": "Me", "counterparty": "Bob", "transaction_subject": "rent from Bob"},
            ),
            (
                "Paid ₹500 for groceries",
                {"amount": 500.0, "category": "grocery", "transaction_direction": "expense", "review_level": "none"},
                {"amount": 500, "transaction_subject": "groceries"},
            ),
            (
                "Paid €12 for coffee",
                {"amount": 12.0, "category": "dining", "transaction_direction": "expense", "review_level": "none"},
                {"amount": 12, "transaction_subject": "coffee"},
            ),
            (
                "Paid $20 at Costco on 05/12/2024",
                {"amount": 20.0, "date": "2024-05-12", "transaction_direction": "expense", "review_level": "none"},
                {"date": "05/12/2024", "amount": 20, "receiver": "Costco", "counterparty": "Costco", "transaction_subject": "Costco"},
            ),
        ]

        for note, expected, overrides in cases:
            with self.subTest(note=note):
                self.assert_subset(cleaned(note, **overrides), expected)

    def test_rule_based_fallback_understands_cancellation_and_amount_words(self):
        cases = [
            ("I quit from Qualitest today", {"recurring_action": "cancel", "counterparty": "Qualitest"}),
            ("I paid 46 bucks for leg warmers", {"amount": 46.0, "category": "shopping"}),
            ("I paid 46 at Costco for cereal", {"amount": 46.0, "category": "grocery"}),
            ("I received a pay of $1,650 from Qualitest", {"amount": 1650.0}),
            ("I paid 1,200 USD for rent", {"amount": 1200.0, "category": "rent"}),
            ("Paid ₹500 for groceries", {"amount": 500.0, "category": "grocery"}),
            ("I get paid biweekly by Acme for 1200$", {"recurring_frequency": "biweekly", "recurring_interval_days": 14}),
            ("I get paid every other week by Acme for 1200$", {"recurring_frequency": "biweekly", "recurring_interval_days": 14}),
            ("Acme pays me 1200$ twice a month", {"recurring_frequency": "custom_days", "recurring_interval_days": 15}),
            ("I receive 1650$ every 15 days from Qualitest", {"recurring_frequency": "custom_days", "recurring_interval_days": 15}),
            ("I no longer use Netflix", {"recurring_action": "cancel", "counterparty": "Netflix"}),
            ("My contract with Acme ended today", {"recurring_action": "cancel", "counterparty": "Acme"}),
            ("Tenant Bob moved out today", {"recurring_action": "cancel", "counterparty": "Bob"}),
        ]

        for note, expected in cases:
            with self.subTest(note=note):
                self.assert_subset(fallback_without_conversion(note, "USD"), expected)

    def test_rule_based_fallback_keeps_core_parser_features_current(self):
        cases = [
            (
                "Purchased Glenlivet whiskey for 56$ on April 5th 2024.",
                {
                    "date": "2024-04-05",
                    "amount": 56.0,
                    "category": "entertainment",
                    "transaction_direction": "expense",
                    "transaction_subject": "Glenlivet whiskey",
                    "sender": "Me",
                },
            ),
            (
                "I bought milk and eggs for 18 bucks at Natural Dairy.",
                {
                    "amount": 18.0,
                    "category": "grocery",
                    "transaction_direction": "expense",
                    "counterparty": "Natural Dairy",
                    "receiver": "Natural Dairy",
                    "transaction_subject": "milk and eggs",
                    "subject_quality": "clear",
                },
            ),
            (
                "I purchased Zomato pro on July 15th 1984 for 7$",
                {
                    "date": "1984-07-15",
                    "amount": 7.0,
                    "category": "subscription",
                    "recurring_action": "create",
                    "recurring_frequency": "monthly",
                    "review_level": "quick",
                },
            ),
            (
                "I got a job at Qualitest on March 1st 2026. For every 15 days I receive a pay of 1650$",
                {
                    "date": "2026-03-01",
                    "amount": 1650.0,
                    "category": "salary",
                    "transaction_direction": "income",
                    "counterparty": "Qualitest",
                    "recurring_action": "create",
                    "recurring_frequency": "custom_days",
                    "recurring_interval_days": 15,
                    "review_level": "quick",
                },
            ),
            (
                "I quit from Qualitest today",
                {
                    "amount": 0.0,
                    "category": "salary",
                    "transaction_direction": "income",
                    "counterparty": "Qualitest",
                    "recurring_action": "cancel",
                    "status": "cancelled",
                    "review_level": "quick",
                },
            ),
        ]

        for note, expected in cases:
            with self.subTest(note=note):
                self.assert_subset(fallback_without_conversion(note, "USD"), expected)

    def test_rule_based_fallback_triggers_currency_conversion(self):
        result = fallback_with_fake_conversion(
            "Paid 12 CHF for coffee",
            user_currency="USD",
            rate=1.25,
        )

        self.assertEqual(result["amount"], 15.0)
        self.assertEqual(result["original_amount"], 12.0)
        self.assertEqual(result["original_currency"], "CHF")
        self.assertTrue(result["requires_conversion_confirmation"])

    def test_parse_note_uses_configured_openai_provider(self):
        note = "I paid 12 dollars for coffee"
        original_provider = parser.os.environ.get("LLM_PROVIDER")
        original_call_openai = parser.call_openai
        original_converter = parser.apply_currency_conversion

        def fake_call_openai(prompt):
            self.assertIn(note, prompt)
            return base_model_output(
                note,
                amount=12,
                transaction_subject="coffee",
                category="dining",
                transaction_direction="expense",
                subject_quality="clear",
                sender="Me",
            )

        parser.os.environ["LLM_PROVIDER"] = "openai"
        parser.call_openai = fake_call_openai
        parser.apply_currency_conversion = without_currency_conversion

        try:
            result = parser.parse_note(
                parser.NoteInput(raw_text=note, currency="USD"),
                current_user=SimpleNamespace(default_currency="USD"),
            )
        finally:
            if original_provider is None:
                parser.os.environ.pop("LLM_PROVIDER", None)
            else:
                parser.os.environ["LLM_PROVIDER"] = original_provider
            parser.call_openai = original_call_openai
            parser.apply_currency_conversion = original_converter

        self.assertEqual(result["amount"], 12.0)
        self.assertEqual(result["category"], "dining")
        self.assertEqual(result["review_level"], "none")

    def test_parse_note_falls_back_when_llm_provider_fails(self):
        note = "I quit from Qualitest today"
        original_call_llm = parser.call_llm
        original_converter = parser.apply_currency_conversion

        def failing_call_llm(prompt):
            raise RuntimeError("simulated provider failure")

        parser.call_llm = failing_call_llm
        parser.apply_currency_conversion = without_currency_conversion

        try:
            result = parser.parse_note(
                parser.NoteInput(raw_text=note, currency="USD"),
                current_user=SimpleNamespace(default_currency="USD"),
            )
        finally:
            parser.call_llm = original_call_llm
            parser.apply_currency_conversion = original_converter

        self.assertEqual(result["recurring_action"], "cancel")
        self.assertEqual(result["counterparty"], "Qualitest")


class CurrencyConversionRuleTests(unittest.TestCase):
    def assert_subset(self, actual, expected):
        for key, value in expected.items():
            self.assertEqual(actual.get(key), value, f"{key}: {actual}")

    def test_detects_currency_next_to_amount(self):
        cases = [
            ("Paid €12 for coffee", "USD", "EUR"),
            ("Paid 500 INR for groceries", "USD", "INR"),
            ("Paid ₹500 for groceries", "USD", "INR"),
            ("Paid 20 pounds for lunch", "USD", "GBP"),
            ("Paid 12 CHF for coffee", "USD", "CHF"),
            ("Paid 12 Swiss francs for coffee", "USD", "CHF"),
            ("Paid 12 Fr for coffee", "USD", "CHF"),
            ("Paid $20 for lunch", "INR", "USD"),
            ("Paid $20 for lunch", "USD", "USD"),
            ("Paid 35 bucks for dinner", "INR", "USD"),
        ]

        for note, user_currency, expected_currency in cases:
            with self.subTest(note=note, user_currency=user_currency):
                self.assertEqual(
                    detect_transaction_currency(note, user_currency),
                    expected_currency,
                )

    def test_parser_converts_foreign_currency_before_confirmation(self):
        result = cleaned_with_fake_conversion(
            "I bought coffee for €10 at Cafe Roma",
            "USD",
            rate=1.2,
            amount=10,
            receiver="Cafe Roma",
            counterparty="Cafe Roma",
            category="dining",
            transaction_direction="expense",
            transaction_subject="coffee",
            subject_quality="clear",
        )

        self.assert_subset(
            result,
            {
                "amount": 12.0,
                "currency": "USD",
                "original_amount": 10.0,
                "original_currency": "EUR",
                "converted_amount": 12.0,
                "converted_currency": "USD",
                "exchange_rate": 1.2,
                "exchange_rate_date": "2026-05-16",
                "exchange_rate_source": "unit-test",
                "requires_conversion_confirmation": True,
                "review_level": "quick",
            },
        )

    def test_parser_converts_usd_note_for_inr_user(self):
        result = cleaned_with_fake_conversion(
            "I paid $20 for lunch at Subway",
            "INR",
            rate=83.0,
            amount=20,
            receiver="Subway",
            counterparty="Subway",
            category="dining",
            transaction_direction="expense",
            transaction_subject="lunch",
            subject_quality="clear",
        )

        self.assert_subset(
            result,
            {
                "amount": 1660.0,
                "currency": "INR",
                "original_amount": 20.0,
                "original_currency": "USD",
                "converted_amount": 1660.0,
                "converted_currency": "INR",
                "requires_conversion_confirmation": True,
                "review_level": "quick",
            },
        )

    def test_parser_converts_swiss_franc_note(self):
        result = cleaned_with_fake_conversion(
            "I paid 12 CHF for coffee at Zurich Cafe",
            "USD",
            rate=1.15,
            amount=12,
            receiver="Zurich Cafe",
            counterparty="Zurich Cafe",
            category="dining",
            transaction_direction="expense",
            transaction_subject="coffee",
            subject_quality="clear",
        )

        self.assert_subset(
            result,
            {
                "amount": 13.8,
                "currency": "USD",
                "original_amount": 12.0,
                "original_currency": "CHF",
                "converted_amount": 13.8,
                "converted_currency": "USD",
                "exchange_rate": 1.15,
                "requires_conversion_confirmation": True,
                "review_level": "quick",
            },
        )

    def test_failed_rate_lookup_forces_full_review(self):
        def failing_fetcher(from_currency, to_currency):
            raise ValueError("network unavailable")

        parsed = base_model_output(
            "Paid €10 for coffee",
            amount=10,
            category="dining",
            transaction_subject="coffee",
            subject_quality="clear",
            review_level="none",
        )

        result = apply_currency_conversion(
            parsed,
            "Paid €10 for coffee",
            "USD",
            rate_fetcher=failing_fetcher,
        )

        self.assertEqual(result["currency"], "EUR")
        self.assertEqual(result["review_level"], "full")
        self.assertIn("exchange_rate", result["missing_fields"])
        self.assertFalse(result["requires_conversion_confirmation"])


class RecurringAndReportRuleTests(unittest.TestCase):
    def test_deleting_original_transaction_deletes_linked_recurring_rule(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        models.Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            user = models.User(
                id="user-1",
                first_name="Test",
                last_name="User",
                email="test@example.com",
                password_hash="hash",
            )
            transaction = models.Transaction(
                id="tx-1",
                user_id=user.id,
                raw_text="I get paid by Acme every 15 days",
                date=date(2026, 3, 1),
                amount=1650,
                currency="USD",
                sender="Acme",
                receiver="Me",
                counterparty="Acme",
                category="salary",
                transaction_direction="income",
                source="other",
                origin_type="note",
                status="completed",
                is_recurring=True,
                confidence_score=0.98,
                review_level="quick",
                transaction_subject="salary from Acme",
                subject_quality="clear",
                missing_fields=[],
                ambiguity_reasons=[],
            )
            linked_rule = models.RecurringTransaction(
                id="rule-1",
                user_id=user.id,
                name="Acme",
                amount=1650,
                currency="USD",
                category="salary",
                transaction_direction="income",
                source="other",
                frequency="custom_days",
                interval_days=15,
                start_date=date(2026, 3, 1),
                created_from_transaction_id=transaction.id,
            )
            other_rule = models.RecurringTransaction(
                id="rule-2",
                user_id=user.id,
                name="Zomato",
                amount=7,
                currency="USD",
                category="subscription",
                transaction_direction="expense",
                source="other",
                frequency="monthly",
                start_date=date(2026, 1, 15),
                created_from_transaction_id="another-tx",
            )

            db.add_all([user, transaction, linked_rule, other_rule])
            db.commit()

            response = delete_transaction(transaction.id, db=db, current_user=user)

            self.assertEqual(response["deleted_recurring_rules"], 1)
            self.assertIsNone(db.get(models.Transaction, transaction.id))
            self.assertIsNone(db.get(models.RecurringTransaction, linked_rule.id))
            self.assertIsNotNone(db.get(models.RecurringTransaction, other_rule.id))
        finally:
            db.close()

    def test_fuzzy_match_requires_confirmation_for_close_names(self):
        rules = [
            SimpleNamespace(id="1", name="Qualitest Salary"),
            SimpleNamespace(id="2", name="Quality Gym"),
            SimpleNamespace(id="3", name="Zomato Pro"),
        ]

        best, possible = find_best_recurring_match(rules, "Qualitest")

        self.assertEqual(best["rule"].id, "1")
        self.assertGreaterEqual(best["score"], 0.82)
        self.assertTrue(any(item["rule"].id == "2" for item in possible))

    def test_report_projection_windows_and_intervals(self):
        biweekly = SimpleNamespace(
            id="biweekly",
            name="Acme Salary",
            amount=1200,
            currency="USD",
            category="salary",
            transaction_direction="income",
            source="other",
            frequency="biweekly",
            interval_days=14,
            start_date=date(2026, 5, 13),
            end_date=None,
        )
        custom = SimpleNamespace(
            id="custom",
            name="Qualitest Salary",
            amount=1650,
            currency="USD",
            category="salary",
            transaction_direction="income",
            source="other",
            frequency="custom_days",
            interval_days=15,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 4, 20),
        )
        monthly = SimpleNamespace(
            id="monthly",
            name="Zomato",
            amount=7,
            currency="USD",
            category="subscription",
            transaction_direction="expense",
            source="other",
            frequency="monthly",
            interval_days=None,
            start_date=date(1984, 7, 15),
            end_date=date(1984, 9, 1),
            due_day="15",
        )

        self.assertEqual(
            [d.isoformat() for d in get_recurring_occurrence_dates(biweekly, 2026, 5)],
            ["2026-05-13", "2026-05-27"],
        )
        self.assertEqual(
            [d.isoformat() for d in get_recurring_occurrence_dates(custom, 2026, 3)],
            ["2026-03-01", "2026-03-16", "2026-03-31"],
        )
        self.assertEqual(
            [d.isoformat() for d in get_recurring_occurrence_dates(custom, 2026, 4)],
            ["2026-04-15"],
        )
        self.assertEqual(
            [d.isoformat() for d in get_recurring_occurrence_dates(monthly, 1984, 10)],
            [],
        )

    def test_recurring_projection_direction(self):
        income_rule = SimpleNamespace(
            id="income",
            name="Qualitest",
            amount=1650,
            currency="USD",
            category="salary",
            transaction_direction="income",
            source="other",
        )
        expense_rule = SimpleNamespace(
            id="expense",
            name="Zomato",
            amount=7,
            currency="USD",
            category="subscription",
            transaction_direction="expense",
            source="other",
        )

        income = recurring_to_dict(income_rule, date(2026, 3, 1))
        expense = recurring_to_dict(expense_rule, date(2026, 3, 1))

        self.assertEqual(income["sender"], "Qualitest")
        self.assertEqual(income["receiver"], "Me")
        self.assertEqual(expense["sender"], "Me")
        self.assertEqual(expense["receiver"], "Zomato")


class UserPreferenceRuleTests(unittest.TestCase):
    def test_currency_update_normalizes_supported_currency(self):
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        models.Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()

        try:
            user = models.User(
                id="user-1",
                first_name="Test",
                last_name="User",
                email="test@example.com",
                password_hash="hash",
                default_currency="USD",
            )
            db.add(user)
            db.commit()

            response = update_currency(
                user.id,
                " chf ",
                db=db,
                current_user=user,
            )

            self.assertEqual(response["currency"], "CHF")
            self.assertEqual(db.get(models.User, user.id).default_currency, "CHF")
        finally:
            db.close()

    def test_currency_update_rejects_unsupported_currency(self):
        user = SimpleNamespace(id="user-1")
        db = SimpleNamespace()

        with self.assertRaises(HTTPException) as context:
            update_currency(
                "user-1",
                "DOGE",
                db=db,
                current_user=user,
            )

        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
