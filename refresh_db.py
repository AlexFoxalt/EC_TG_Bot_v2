from src.db.refresh_db import refresh_db
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    refresh_db()
