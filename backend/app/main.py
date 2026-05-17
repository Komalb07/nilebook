from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from parser import router as parser_router
from transactions import router as transaction_router
from auth import router as auth_router
import models
from database import init_db
from report import router as report_router
from users import router as user_router
import recurring
import os

app = FastAPI()

init_db()

def get_cors_origins():
    raw_origins = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )

    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parser_router)
app.include_router(transaction_router)
app.include_router(auth_router)
app.include_router(report_router)
app.include_router(user_router)
app.include_router(recurring.router)


@app.get("/")
def read_root():
    return {"message": "Finance Tracker backend is running"}
