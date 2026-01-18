import os
from typing import Annotated
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.models.heartbeat import Heartbeat
from src.logger.main import logger
from src.utils import get_database_url

HEARTBEAT_PATH = os.getenv("HEARTBEAT_PATH", "/heartbeat").strip()
HEARTBEAT_TOKEN = os.getenv("HEARTBEAT_TOKEN", "").strip()
HEARTBEAT_ID = 1

engine = create_async_engine(get_database_url(), pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)

auth_provider = HTTPBearer()


def _normalize_path(path: str) -> str:
    if not path:
        return "/heartbeat"
    if not path.startswith("/"):
        return f"/{path}"
    return path


def _validate_token(token: str) -> None:
    if token != HEARTBEAT_TOKEN:
        logger.warning(
            "Heartbeat unauthorized",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )


async def _get_sql_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


async def _get_or_create_heartbeat(
    session: AsyncSession,
) -> Heartbeat:
    result = await session.execute(select(Heartbeat).where(Heartbeat.id == HEARTBEAT_ID))
    heartbeat = result.scalar_one_or_none()
    if heartbeat is None:
        heartbeat = Heartbeat(id=HEARTBEAT_ID)
        session.add(heartbeat)
    return heartbeat


app = FastAPI(title="Pi Heartbeat Listener", version="1.0.0")
HEARTBEAT_PATH = _normalize_path(HEARTBEAT_PATH)


@app.on_event("startup")
async def _on_startup() -> None:
    logger.info(
        "Heartbeat listener starting",
        extra={
            "path": HEARTBEAT_PATH,
            "auth_required": bool(HEARTBEAT_TOKEN),
        },
    )


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    await engine.dispose()


@app.get(HEARTBEAT_PATH)
async def listen_heartbeat(
    timestamp: int,
    token: Annotated[str, Depends(auth_provider)],
    sql_session: AsyncSession = Depends(_get_sql_session),
) -> JSONResponse:
    if HEARTBEAT_TOKEN:
        _validate_token(token.credentials)

    heartbeat_row = await _get_or_create_heartbeat(sql_session)
    ts_value = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    heartbeat_row.timestamp = ts_value
    await sql_session.commit()

    payload = {
        "status": "ok",
        "timestamp": heartbeat_row.timestamp.isoformat(),
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=payload)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok"})
