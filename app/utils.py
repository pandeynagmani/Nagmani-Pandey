import os
import io
import qrcode
from functools import wraps

from cryptography.fernet import Fernet
from flask import abort, flash, redirect, url_for
from flask_login import current_user

from config.settings import AADHAAR_KEY_FILE, UPLOAD_DIR


def role_required(*roles):
    """Decorator to restrict access to specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _get_or_create_key():
    if os.path.exists(AADHAAR_KEY_FILE):
        with open(AADHAAR_KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    os.makedirs(os.path.dirname(AADHAAR_KEY_FILE), exist_ok=True)
    with open(AADHAAR_KEY_FILE, "wb") as f:
        f.write(key)
    return key


def encrypt_aadhaar(aadhaar_number: str) -> str:
    """Encrypt an Aadhaar number for storage."""
    key = _get_or_create_key()
    fernet = Fernet(key)
    return fernet.encrypt(aadhaar_number.encode()).decode()


def decrypt_aadhaar(encrypted: str) -> str:
    """Decrypt an Aadhaar number."""
    key = _get_or_create_key()
    fernet = Fernet(key)
    return fernet.decrypt(encrypted.encode()).decode()


def mask_aadhaar(aadhaar_number: str) -> str:
    """Mask Aadhaar number: XXXXXXXX1234."""
    if len(aadhaar_number) >= 4:
        return "X" * (len(aadhaar_number) - 4) + aadhaar_number[-4:]
    return aadhaar_number


def generate_qr_code(data: str, filename: str) -> str:
    """Generate a QR code image and save to uploads."""
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    qr_dir = os.path.join(UPLOAD_DIR, "qr_codes")
    os.makedirs(qr_dir, exist_ok=True)
    filepath = os.path.join(qr_dir, filename)
    img.save(filepath)
    return f"uploads/qr_codes/{filename}"


def calculate_kra(syllabus_pct, attendance_pct, homework_pct):
    """Calculate KRA score (weighted average)."""
    return round(
        (syllabus_pct * 0.40) + (attendance_pct * 0.35) + (homework_pct * 0.25),
        2,
    )


def calculate_salary(base_salary, kra_score, attendance_days, working_days, advance=0, deductions=0, bonus=0):
    """Calculate total payable salary based on KRA and attendance."""
    if working_days == 0:
        attendance_ratio = 0
    else:
        attendance_ratio = attendance_days / working_days

    kra_factor = kra_score / 100.0 if kra_score <= 100 else 1.0
    payable = base_salary * attendance_ratio * (0.7 + 0.3 * kra_factor)
    payable = payable + bonus - advance - deductions
    return round(max(payable, 0), 2)
