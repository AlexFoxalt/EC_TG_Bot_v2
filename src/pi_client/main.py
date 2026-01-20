import os
import asyncio
from datetime import datetime, UTC

import httpx

from src.logger.main import logger


def _build_heartbeat_url(droplet_ip: str, droplet_port: int, heartbeat_path: str) -> str:
    scheme = "http"
    host = droplet_ip.strip()
    port = str(droplet_port).strip()
    path = heartbeat_path.strip() or "/heartbeat"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{scheme}://{host}:{port}{path}"


async def _astart_pi_client() -> None:
    droplet_ip = os.getenv("DROPLET_IP", "localhost")
    droplet_port = int(os.getenv("DROPLET_PORT", "5566"))
    heartbeat_interval = int(os.getenv("SEND_HEARTBEAT_INTERVAL_SECONDS", "10"))
    heartbeat_path = os.getenv("HEARTBEAT_PATH", "/heartbeat")
    heartbeat_timeout = float(os.getenv("HEARTBEAT_TIMEOUT", "5"))
    heartbeat_token = os.getenv("HEARTBEAT_TOKEN", "")
    heartbeat_label = os.getenv("HEARTBEAT_LABEL", "UNKNOWN")

    logger.info("Starting heartbeat...")
    url = _build_heartbeat_url(droplet_ip, droplet_port, heartbeat_path)
    timeout = httpx.Timeout(heartbeat_timeout)
    headers = {}
    if heartbeat_token:
        headers["Authorization"] = f"Bearer {heartbeat_token}"
    if not headers:
        headers = None
    logger.info(
        f"Heartbeat configured. url: {url}, label: {heartbeat_label}, interval_sec: {heartbeat_interval}, timeout_sec: {heartbeat_timeout}",
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            try:
                params = {"timestamp": int(datetime.now(UTC).timestamp()), "label": heartbeat_label}
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                logger.info(
                    f"Heartbeat sent. Status code: {response.status_code}",
                )
            except httpx.RequestError as exc:
                logger.warning(f"Heartbeat request failed. Err: {exc} | URL: {url}")
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    f"Heartbeat response error. Status code: {exc.response.status_code} | Body: {exc.response.text[:500]}",
                )
            except Exception as exc:
                logger.exception("Unexpected heartbeat error", exc_info=exc)

            await asyncio.sleep(heartbeat_interval)


def start_pi_client() -> None:
    asyncio.run(_astart_pi_client())
