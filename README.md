# Nilebook

Nilebook is a full-stack personal finance journal app. It lets users write money-related notes in normal language and turns those notes into structured transactions.

Instead of filling out a long form, the user can simply write something like:

```txt
I bought coffee for 5 dollars using cash
```

Nilebook reads the note, extracts the important details, saves the transaction, and uses it to generate reports.

**Live App:** https://nilebook-blond.vercel.app

---

## Overview

Nilebook was built to make personal finance tracking easier and faster. Most finance apps require users to manually enter every detail such as amount, date, category, payment source, and transaction type. Nilebook takes a different approach.

The user writes a simple note, and the app understands the transaction from that note.

For example:

```txt
I paid 120 dollars for groceries using my credit card
```

Nilebook can extract:

- Amount: 120
- Category: Groceries
- Source: Credit card
- Direction: Money out

The app also supports income, recurring transactions, cancellations, reports, user accounts, email verification, and password reset.

---

## Features

### User Authentication

Nilebook includes a complete authentication flow:

- User signup
- Email verification
- Login
- JWT-based protected routes
- Forgot password
- Reset password
- Account deletion

### Natural Language Transaction Entry

Users can add transactions by typing regular sentences.

Examples:

```txt
I bought coffee for 5 dollars using cash
```

```txt
I received 500 dollars from Rahul using checking
```

```txt
I paid 120 dollars for groceries using my credit card
```

The backend parses the note and extracts useful transaction fields.

### Parsed Transaction Fields

Nilebook extracts and stores information such as:

- Date
- Sender
- Receiver
- Amount
- Category
- Source
- Transaction direction
- Currency
- Recurring details when applicable

### Recurring Transactions

Nilebook supports recurring income and recurring expenses.

Examples:

```txt
Netflix charges me 15 dollars every month
```

```txt
I receive 1650 dollars every 15 days from my job
```

Supported recurring intervals include:

- Weekly
- Biweekly
- Monthly
- Yearly
- Custom day intervals

Recurring transactions are handled with rules so they do not appear before their start date or after cancellation.

### Recurring Cancellation

Users can cancel recurring transactions using natural language.

Example:

```txt
Cancel my Netflix subscription
```

The app attempts to match the cancellation request with the correct recurring transaction.

### Reports

Nilebook provides financial reports for:

- Year
- Month
- Week

Reports include:

- Total money in
- Total money out
- Net flow
- Transaction breakdowns

### Profile Settings

Users can update profile settings such as their default currency.

### Currency Support

Nilebook supports default currency settings and includes currency conversion support when needed.

### Email Support

Nilebook uses Resend for:

- Email verification
- Password reset emails

---

## Tech Stack

### Frontend

- Next.js
- React
- TypeScript
- CSS

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT authentication

### Database

- PostgreSQL for production
- SQLite for local development

### External Services

- OpenAI API for natural language parsing
- Resend for emails
- Exchange rate API for currency conversion

### Deployment

- Frontend deployed on Vercel
- Backend deployed on Render
- PostgreSQL database hosted on Render

---

## Project Structure

```txt
nilebook/
│
├── backend/
│   ├── app/
│   │   ├── auth.py
│   │   ├── currency_conversion.py
│   │   ├── database.py
│   │   ├── email_service.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── parser.py
│   │   ├── recurring.py
│   │   ├── report.py
│   │   ├── schemas.py
│   │   ├── transactions.py
│   │   └── users.py
│   │
│   ├── tests/
│   │   └── test_nilebook_rules.py
│   │
│   ├── requirements.txt
│   ├── runtime.txt
│   ├── README.md
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── components/
│   │   │   └── Navbar.tsx
│   │   │
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   │
│   │   ├── forgot-password/
│   │   │   └── page.tsx
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── clientStorage.ts
│   │   │   └── format.ts
│   │   │
│   │   ├── login/
│   │   │   └── page.tsx
│   │   │
│   │   ├── profile/
│   │   │   └── page.tsx
│   │   │
│   │   ├── report/
│   │   │   └── page.tsx
│   │   │
│   │   ├── reset-password/
│   │   │   └── page.tsx
│   │   │
│   │   ├── signup/
│   │   │   └── page.tsx
│   │   │
│   │   ├── verify-email/
│   │   │   └── page.tsx
│   │   │
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   │
│   ├── public/
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   └── .env.example
│
├── .gitignore
└── README.md
```

---

## Backend Files

### `backend/app/main.py`

Main FastAPI entry point. It creates the app, configures CORS, creates database tables, and includes the app routers.

### `backend/app/database.py`

Handles database connection and session creation. It supports SQLite locally and PostgreSQL in production.

### `backend/app/models.py`

Contains SQLAlchemy database models for users, transactions, and recurring transactions.

### `backend/app/schemas.py`

Contains Pydantic schemas used for request and response validation.

### `backend/app/auth.py`

Handles signup, login, password hashing, JWT token creation, email verification, and password reset logic.

### `backend/app/email_service.py`

Handles email sending through Resend. Used for verification emails and password reset emails.

### `backend/app/parser.py`

Handles natural language finance note parsing. It uses an LLM provider when available and includes fallback logic.

### `backend/app/currency_conversion.py`

Handles exchange rate lookup and currency conversion metadata.

### `backend/app/transactions.py`

Handles transaction creation, retrieval, update, and deletion.

### `backend/app/recurring.py`

Handles recurring transaction creation, recurring transaction expansion, and cancellation logic.

### `backend/app/report.py`

Handles yearly, monthly, and weekly finance reports.

### `backend/app/users.py`

Handles user profile-related routes such as updating default currency and account deletion.

### `backend/tests/test_nilebook_rules.py`

Contains backend tests for important Nilebook rules, especially recurring transaction behavior and parser-related logic.

---

## Frontend Files

### `frontend/app/page.tsx`

Main landing page.

### `frontend/app/signup/page.tsx`

Signup page where users create an account.

### `frontend/app/verify-email/page.tsx`

Email verification page.

### `frontend/app/login/page.tsx`

Login page.

### `frontend/app/forgot-password/page.tsx`

Page where users request a password reset email.

### `frontend/app/reset-password/page.tsx`

Page where users set a new password.

### `frontend/app/dashboard/page.tsx`

Main dashboard where users enter finance notes, review parsed details, and save transactions.

### `frontend/app/report/page.tsx`

Reports page for yearly, monthly, and weekly financial summaries.

### `frontend/app/profile/page.tsx`

Profile page where users can update settings such as default currency.

### `frontend/app/components/Navbar.tsx`

Navigation bar used across the app.

### `frontend/app/lib/api.ts`

Frontend API helper used to call the backend.

### `frontend/app/lib/clientStorage.ts`

Safe client-side storage helper used to avoid hydration issues.

### `frontend/app/lib/format.ts`

Formatting helper for dates, currency, and display values.

### `frontend/app/globals.css`

Main styling file for the frontend.

---

## Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Komalb07/nilebook.git
cd nilebook
```

---

## Backend Setup

Go to the backend folder:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside the `backend` folder using `.env.example` as a reference.

Example backend `.env`:

```env
DATABASE_URL=sqlite:///./finance.db
SECRET_KEY=your-secret-key

FRONTEND_URL=http://localhost:3000
BACKEND_CORS_ORIGINS=http://localhost:3000

RESEND_API_KEY=your-resend-api-key
FROM_EMAIL=Nilebook <onboarding@resend.dev>
EMAIL_DELIVERY_MODE=console

LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5-mini
OPENAI_TIMEOUT_SECONDS=60

EXCHANGE_RATE_API_URL=https://open.er-api.com/v6/latest/{base}
EXCHANGE_RATE_SOURCE_NAME=open.er-api.com
EXCHANGE_RATE_TIMEOUT_SECONDS=8
```

Run the backend:

```bash
uvicorn main:app --app-dir app --reload
```

The backend will run at:

```txt
http://localhost:8000
```

---

## Frontend Setup

Open a new terminal and go to the frontend folder:

```bash
cd frontend
```

Install frontend dependencies:

```bash
npm install
```

Create a `.env.local` file inside the `frontend` folder.

Example frontend `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run the frontend:

```bash
npm run dev
```

The frontend will run at:

```txt
http://localhost:3000
```

---

## Running Tests

From the backend folder, run:

```bash
pytest
```

The tests cover important backend behavior such as recurring transaction rules and parser-related logic.

---

## Production Deployment

Nilebook is deployed using:

- Vercel for the frontend
- Render for the backend
- Render PostgreSQL for the production database

### Production Frontend

The frontend is deployed on Vercel.

Production frontend URL:

```txt
https://nilebook-blond.vercel.app
```

The frontend uses this environment variable:

```env
NEXT_PUBLIC_API_URL=https://nilebook-backend.onrender.com
```

### Production Backend

The backend is deployed on Render.

Production backend URL:

```txt
https://nilebook-backend.onrender.com
```

The backend uses environment variables for database connection, authentication, email delivery, LLM parsing, CORS, and currency conversion.

### Production Database

The production database is PostgreSQL hosted on Render.

Local SQLite database files are not included in the repository.

---

## Environment Variables

Environment variables are not committed to GitHub.

The repository includes `.env.example` files to show what values are needed.

Important backend variables:

```env
DATABASE_URL=
SECRET_KEY=
FRONTEND_URL=
BACKEND_CORS_ORIGINS=
RESEND_API_KEY=
FROM_EMAIL=
EMAIL_DELIVERY_MODE=
LLM_PROVIDER=
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_TIMEOUT_SECONDS=
EXCHANGE_RATE_API_URL=
EXCHANGE_RATE_SOURCE_NAME=
EXCHANGE_RATE_TIMEOUT_SECONDS=
```

Important frontend variable:

```env
NEXT_PUBLIC_API_URL=
```

---

## Security Notes

The repository does not include:

- `.env` files
- local database files
- API keys
- deployment secrets
- `node_modules`
- build folders

Secrets are stored only in Render and Vercel environment settings.

---

## Example User Flow

A typical user flow looks like this:

1. User creates an account.
2. User verifies their email.
3. User logs in.
4. User writes a finance note.
5. Nilebook parses the note.
6. User reviews and saves the transaction.
7. The transaction appears in reports.
8. User can view money in, money out, and net flow.

Example note:

```txt
I bought coffee for 5 dollars using cash
```

The app saves it as a structured transaction and includes it in the user’s financial report.

---

## Why I Built This

I built Nilebook because tracking personal finance manually can feel slow and repetitive. Most finance apps ask users to enter every detail one by one. I wanted to make the process feel more natural.

The idea behind Nilebook is simple:

Write what happened with your money, and let the app organize it.

---

## Current Status

Nilebook is currently deployed and working as a full-stack application.

It includes:

- Authentication
- Email verification
- Password reset
- Natural language transaction parsing
- Recurring transactions
- Currency support
- Reports
- Profile settings
- Production deployment

---

## Author

Built by Komal Bhimireddy.
GitHub: https://github.com/Komalb07
