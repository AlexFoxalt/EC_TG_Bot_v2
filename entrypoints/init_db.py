import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.db.init_db import init_db
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    init_db()
