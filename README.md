# Power Status App

![System design](docs/system_design.png)

Telegram bot and heartbeat pipeline to monitor power availability and notify users when the state changes. 

A lightweight client(s) (e.g., Raspberry Pi) sends heartbeats, a server stores them, a scheduler interprets power status, and the bot delivers alerts.

## Architecture overview

Flow (left to right):
1. **pi_client** sends heartbeats to **pi_server** (FastAPI).
2. **pi_server** updates `heartbeat` records in **Postgres**.
3. **scheduler** checks last heartbeat timestamps and writes `statuses` when power changes.
4. **bot** reads new status changes and notifies Telegram users.

Core services:
- **postgres**: data store (`heartbeat`, `statuses`, `users`)
- **pi_server**: heartbeat ingestion API (`/heartbeat`)
- **scheduler**: power status detection loop
- **bot**: Telegram interactions and notifications
- **pi_client**: external heartbeat sender (runs on a device)

## Tech stack

- **Python 3**: core language
- **FastAPI + Uvicorn**: heartbeat HTTP server
- **python-telegram-bot**: Telegram bot
- **SQLAlchemy (async) + asyncpg**: database layer
- **Alembic**: migrations
- **Loguru**: logging
- **Docker + Docker Compose**: local stack
- **Ruff**: linting

## Quick start (Docker Compose)

### 1) Configure environment

```bash
cp .env.example .env
```

Required:
- `POSTGRES_PASSWORD`
- `TELEGRAM_TOKEN`
- `HEARTBEAT_TOKEN` (optional but recommended for auth)
- `HEARTBEAT_LABEL` (label for your client device)

Common optional values:
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PORT`
- `DROPLET_IP`, `DROPLET_PORT` (where pi_client points)
- `HEARTBEAT_PATH` (default `/heartbeat`)
- `SEND_HEARTBEAT_INTERVAL_SECONDS` (pi_client)
- `LISTEN_HEARTBEAT_INTERVAL_SECONDS` (scheduler)
- `BOT_NOTIFICATION_POLL_INTERVAL_SECONDS` (bot)
- `LOG_LEVEL`

### 2) Initialize the database (first time only)

```bash
docker compose up -d postgres
docker compose run --rm bot python entrypoints/init_db.py
```

### 3) Start the stack

```bash
docker compose up -d
```

### 4) Logs and shutdown

```bash
docker compose logs -f
docker compose down
```

## Running locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` from `.env.example`, then run any component:

```bash
# Heartbeat server
python entrypoints/start_pi_server.py

# Heartbeat client (usually runs on a Raspberry Pi)
python entrypoints/start_pi_client.py

# Scheduler
python entrypoints/scheduler.py

# Telegram bot
python entrypoints/bot.py
```

## Project structure

```
entrypoints/          # runnable entrypoints
src/bot/              # telegram bot handlers, jobs, keyboards, lang pack
src/pi_server/        # heartbeat API
src/pi_client/        # heartbeat sender
src/scheduler/        # power status detector
src/db/               # models and init
docs/                 # system design image
```

## Notes

- Postgres is bound to `127.0.0.1` by default in Compose.
- Heartbeat auth is optional; when set, it uses a bearer token.
- This is a pet project README: intentionally lightweight and practical.
