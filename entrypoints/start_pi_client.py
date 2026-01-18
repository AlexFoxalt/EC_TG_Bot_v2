import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.pi_client.main import start_pi_client
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    start_pi_client()
