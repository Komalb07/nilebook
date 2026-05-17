# Nilebook Backend

## Local Development

From the `backend` folder, activate the virtual environment:

```bash
source .venv/bin/activate
```

Start the API without the heavy FastAPI file watcher:

```bash
cd app
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

If you want auto-reload while editing backend code, use this narrower watcher:

```bash
cd app
python -m uvicorn main:app --reload --reload-dir . --host 127.0.0.1 --port 8000
```

Prefer these commands over `fastapi dev app/main.py` on this project. The FastAPI dev command watches the broader backend folder and can be killed by macOS on some local setups.

## Local Email

The local `.env` uses:

```bash
EMAIL_DELIVERY_MODE=console
```

That means signup and password-reset emails are printed in the backend terminal instead of being sent through Resend. Copy the verification or reset link from the terminal while testing locally.
