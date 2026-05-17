from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from models import Base
from pathlib import Path
import os

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = f"sqlite:///{BACKEND_DIR / 'finance.db'}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
if DATABASE_URL.startswith("sqlite:///./"):
    DATABASE_URL = f"sqlite:///{BACKEND_DIR / DATABASE_URL.replace('sqlite:///./', '')}"

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_db():
    Base.metadata.create_all(bind=engine)
    add_missing_columns()


def add_missing_columns():
    inspector = inspect(engine)

    table_names = inspector.get_table_names()

    if "recurring_transactions" in table_names:
        recurring_columns = {
            column["name"]
            for column in inspector.get_columns("recurring_transactions")
        }

        if "interval_days" not in recurring_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE recurring_transactions ADD COLUMN interval_days INTEGER")
                )

    conversion_columns = {
        "original_amount": "FLOAT",
        "original_currency": "VARCHAR",
        "exchange_rate": "FLOAT",
        "exchange_rate_date": "VARCHAR",
        "exchange_rate_source": "VARCHAR",
        "exchange_rate_fetched_at": "DATETIME",
    }

    for table_name in ["transactions", "recurring_transactions"]:
        if table_name not in table_names:
            continue

        existing_columns = {
            column["name"]
            for column in inspector.get_columns(table_name)
        }

        for column_name, column_type in conversion_columns.items():
            if column_name not in existing_columns:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ADD COLUMN {column_name} {column_type}"
                        )
                    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
