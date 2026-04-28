import sqlite3
import os
from datetime import datetime

from flask import g, current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import login_manager


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


class User(UserMixin):
    def __init__(self, id, username, role, full_name):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    row = db.execute(
        "SELECT id, username, role, full_name FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if row:
        return User(row["id"], row["username"], row["role"], row["full_name"])
    return None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('principal','teacher','accountant')),
    full_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    section TEXT DEFAULT 'A'
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    father_name TEXT,
    mother_name TEXT,
    dob TEXT,
    gender TEXT,
    class_id INTEGER REFERENCES classes(id),
    aadhaar_encrypted TEXT,
    address TEXT,
    phone TEXT,
    rfid_tag TEXT UNIQUE,
    qr_code_path TEXT,
    photo_path TEXT,
    admission_date TEXT DEFAULT (date('now')),
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS student_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES students(id),
    date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('present','absent','late')),
    method TEXT DEFAULT 'manual' CHECK(method IN ('manual','rfid','qr')),
    marked_by INTEGER REFERENCES users(id),
    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, date)
);

CREATE TABLE IF NOT EXISTS teacher_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER REFERENCES users(id),
    date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('present','absent','late','half_day')),
    check_in TEXT,
    check_out TEXT,
    UNIQUE(teacher_id, date)
);

CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER REFERENCES users(id),
    date TEXT NOT NULL,
    class_id INTEGER REFERENCES classes(id),
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    notes TEXT,
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS homework (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    daily_log_id INTEGER REFERENCES daily_logs(id),
    student_id INTEGER REFERENCES students(id),
    status TEXT NOT NULL CHECK(status IN ('done','not_done')),
    remarks TEXT
);

CREATE TABLE IF NOT EXISTS syllabus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER REFERENCES classes(id),
    subject TEXT NOT NULL,
    total_topics INTEGER NOT NULL DEFAULT 0,
    completed_topics INTEGER NOT NULL DEFAULT 0,
    teacher_id INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS teacher_salary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER REFERENCES users(id),
    month TEXT NOT NULL,
    year INTEGER NOT NULL,
    base_salary REAL NOT NULL DEFAULT 0,
    kra_score REAL DEFAULT 0,
    attendance_days INTEGER DEFAULT 0,
    working_days INTEGER DEFAULT 0,
    advance REAL DEFAULT 0,
    deductions REAL DEFAULT 0,
    bonus REAL DEFAULT 0,
    total_payable REAL DEFAULT 0,
    approved INTEGER DEFAULT 0,
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    UNIQUE(teacher_id, month, year)
);

CREATE TABLE IF NOT EXISTS fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES students(id),
    fee_type TEXT NOT NULL,
    amount REAL NOT NULL,
    due_date TEXT,
    paid_amount REAL DEFAULT 0,
    paid_date TEXT,
    receipt_no TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','partial','paid')),
    collected_by INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS expenditures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL CHECK(category IN ('lunch','transport','office','other')),
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    recorded_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exam_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER REFERENCES students(id),
    exam_name TEXT NOT NULL,
    subject TEXT NOT NULL,
    max_marks REAL NOT NULL,
    obtained_marks REAL NOT NULL,
    grade TEXT,
    class_id INTEGER REFERENCES classes(id)
);
"""


def init_db(app):
    app.teardown_appcontext(close_db)
    db_path = app.config["DATABASE_PATH"]
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)

    # Seed default admin/principal user
    existing = conn.execute(
        "SELECT id FROM users WHERE username = 'principal'"
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
            (
                "principal",
                generate_password_hash("admin123"),
                "principal",
                "Principal",
            ),
        )

    # Seed default classes
    existing_classes = conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0]
    if existing_classes == 0:
        for cls_name in [
            "Nursery", "LKG", "UKG",
            "1", "2", "3", "4", "5", "6", "7", "8",
        ]:
            conn.execute(
                "INSERT INTO classes (name, section) VALUES (?, ?)",
                (cls_name, "A"),
            )

    # Seed default settings
    defaults = {
        "rfid_enabled": "1",
        "morning_start": "07:30",
        "morning_end": "09:00",
        "afternoon_start": "13:00",
        "afternoon_end": "14:30",
        "server_ip": "0.0.0.0",
        "server_port": "5000",
    }
    for key, value in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    conn.commit()
    conn.close()
