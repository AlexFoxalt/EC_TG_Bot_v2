# Power Status App

![system_design.png](docs/system_design.png)

## Docker Compose (Full Stack)

### Quick start

- **1) Create your env file**:

```bash
cp env.example .env
```

Edit `.env` and set all required variables:
- `POSTGRES_PASSWORD` - Database password
- `TELEGRAM_TOKEN` - Telegram bot token
- `TAPO_EMAIL` - Tapo device email
- `TAPO_PASSWORD` - Tapo device password
- `TAPO_DEVICE_ID` - Tapo device ID

Optional variables:
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER` - Database connection (defaults provided)
- `NOTIFICATION_POLL_INTERVAL_SECONDS` - Bot notification check interval (default: 5)
- `POLL_INTERVAL_SECONDS` - Scheduler polling interval (default: 10)
- `LOG_LEVEL` - Logging level (default: INFO)

- **2) Initialize database** (first time only):

```bash
docker compose up -d postgres
# Wait for postgres to be healthy, then:
docker compose run --rm bot python entrypoints/init_db.py
```

- **3) Start all services**:

```bash
docker compose up -d
```

- **4) View logs**:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f bot
docker compose logs -f scheduler
docker compose logs -f postgres
```

- **5) Stop services**:

```bash
docker compose down
```

### Services

- **postgres**: PostgreSQL database
- **bot**: Telegram bot application
- **scheduler**: Device polling scheduler

### Notes / best practices baked in

- **Auth**: Initialized with **SCRAM-SHA-256** (`POSTGRES_INITDB_ARGS` + `password_encryption`).
- **Networking**: Postgres port is bound to **127.0.0.1** by default (not exposed to LAN).
- **Data safety**: Uses a named volume (`postgres_data`) and `PGDATA` subdirectory.
- **Healthchecks**: All services have healthchecks for proper dependency management.
- **Security**: Services run as non-root user (`appuser`).
- **Multi-stage builds**: Optimized Docker images with minimal size.
- **Logging**: JSON file driver with rotation (10MB max, 3 files).

## Scheduler (poll Tapo device -> write `events` on change)

### Env vars

- **DB**:
  - `DATABASE_URL` (preferred), example: `postgresql+asyncpg://app:...@127.0.0.1:5432/app`
  - or: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **Tapo**: `TAPO_EMAIL`, `TAPO_PASSWORD`, `TAPO_DEVICE_ID`
- **Polling**: `POLL_INTERVAL_SECONDS` (default `10`)

### Run

```bash
python3 -m scheduler.main
```
