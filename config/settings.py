import os
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "app", "static", "uploads")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(DATA_DIR, "school_erp.db")
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

SCHOOL_NAME = "Maa Kamala Public School"
SCHOOL_ADDRESS = "Rokdi, Karchhana, Prayagraj"
SCHOOL_HEADER = f"{SCHOOL_NAME} | {SCHOOL_ADDRESS}"
FOOTER_TEXT = "Developed and Powered by Sant Digital Solution"

# Server defaults
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 5000

# RFID defaults
RFID_ENABLED = True
MORNING_START = "07:30"
MORNING_END = "09:00"
AFTERNOON_START = "13:00"
AFTERNOON_END = "14:30"

# Aadhaar encryption key file
AADHAAR_KEY_FILE = os.path.join(DATA_DIR, "aadhaar.key")
