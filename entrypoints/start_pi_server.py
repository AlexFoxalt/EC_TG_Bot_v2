import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import uvicorn
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()
    host = os.getenv("PI_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("PI_SERVER_PORT", "5566"))
    log_level = os.getenv("PI_SERVER_LOG_LEVEL", "info")
    uvicorn.run(
        "src.pi_server.main:app",
        host=host,
        port=port,
        log_level=log_level,
    )
