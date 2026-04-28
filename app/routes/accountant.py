import os
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import get_db
from app.utils import role_required, encrypt_aadhaar, generate_qr_code
from config.settings import UPLOAD_DIR

accountant_bp = Blueprint("accountant", __name__)


@accountant_bp.route("/dashboard")
@login_required
@role_required("accountant", "principal")
def dashboard():
    db = get_db()
    total_students = db.execute(
        "SELECT COUNT(*) as cnt FROM students WHERE is_active = 1"
    ).fetchone()["cnt"]
    total_fees_collected = db.execute(
        "SELECT COALESCE(SUM(paid_amount), 0) as total FROM fees"
    ).fetchone()["total"]
    pending_fees = db.execute(
        "SELECT COALESCE(SUM(amount - paid_amount), 0) as total FROM fees WHERE status != 'paid'"
    ).fetchone()["total"]
    total_expenditure = db.execute(
        "SELECT COALESCE(SUM(amount), 0) as total FROM expenditures"
    ).fetchone()["total"]

    recent_fees = db.execute(
        "SELECT f.*, s.full_name, s.roll_no FROM fees f "
        "JOIN students s ON f.student_id = s.id "
        "ORDER BY f.paid_date DESC LIMIT 10"
    ).fetchall()

    return render_template(
        "accountant/dashboard.html",
        total_students=total_students,
        total_fees_collected=total_fees_collected,
        pending_fees=pending_fees,
        total_expenditure=total_expenditure,
        recent_fees=recent_fees,
    )


@accountant_bp.route("/admission", methods=["GET", "POST"])
@login_required
@role_required("accountant", "principal")
def admission():
    db = get_db()
    classes = db.execute("SELECT * FROM classes ORDER BY name").fetchall()

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        father_name = request.form.get("father_name", "").strip()
        mother_name = request.form.get("mother_name", "").strip()
        dob = request.form.get("dob", "")
        gender = request.form.get("gender", "")
        class_id = request.form.get("class_id")
        aadhaar = request.form.get("aadhaar", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        rfid_tag = request.form.get("rfid_tag", "").strip() or None

        # Generate roll number
        cls = db.execute("SELECT name FROM classes WHERE id = ?", (class_id,)).fetchone()
        count = db.execute(
            "SELECT COUNT(*) as cnt FROM students WHERE class_id = ?", (class_id,)
        ).fetchone()["cnt"]
        year_short = str(date.today().year)[-2:]
        roll_no = f"{cls['name']}-{year_short}-{count + 1:03d}"

        # Encrypt Aadhaar
        aadhaar_encrypted = encrypt_aadhaar(aadhaar) if aadhaar else None

        # Handle photo upload
        photo_path = None
        if "photo" in request.files:
            file = request.files["photo"]
            if file and file.filename:
                filename = secure_filename(f"{roll_no}_{file.filename}")
                photo_dir = os.path.join(UPLOAD_DIR, "photos")
                os.makedirs(photo_dir, exist_ok=True)
                file.save(os.path.join(photo_dir, filename))
                photo_path = f"uploads/photos/{filename}"

        # Generate QR code with student info
        qr_data = f"Roll:{roll_no}|Name:{full_name}|Class:{cls['name']}|School:Maa Kamala Public School"
        qr_path = generate_qr_code(qr_data, f"{roll_no}_qr.png")

        db.execute(
            "INSERT INTO students (roll_no, full_name, father_name, mother_name, dob, gender, "
            "class_id, aadhaar_encrypted, address, phone, rfid_tag, qr_code_path, photo_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                roll_no, full_name, father_name, mother_name, dob, gender,
                class_id, aadhaar_encrypted, address, phone, rfid_tag, qr_path, photo_path,
            ),
        )
        db.commit()
        flash(f"Student admitted successfully! Roll No: {roll_no}", "success")
        return redirect(url_for("accountant.admission"))

    return render_template("accountant/admission.html", classes=classes)


@accountant_bp.route("/students")
@login_required
@role_required("accountant", "principal")
def students():
    db = get_db()
    class_id = request.args.get("class_id", "")
    search = request.args.get("search", "").strip()
    classes = db.execute("SELECT * FROM classes ORDER BY name").fetchall()

    query = (
        "SELECT s.*, c.name as class_name FROM students s "
        "JOIN classes c ON s.class_id = c.id WHERE s.is_active = 1"
    )
    params = []

    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)
    if search:
        query += " AND (s.full_name LIKE ? OR s.roll_no LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY s.roll_no"
    students_list = db.execute(query, params).fetchall()

    return render_template(
        "accountant/students.html",
        students=students_list,
        classes=classes,
        selected_class=class_id,
        search=search,
    )


@accountant_bp.route("/fees", methods=["GET", "POST"])
@login_required
@role_required("accountant", "principal")
def fees():
    db = get_db()

    if request.method == "POST":
        student_id = request.form.get("student_id")
        fee_type = request.form.get("fee_type", "").strip()
        amount = float(request.form.get("amount", 0))
        paid_amount = float(request.form.get("paid_amount", 0))
        due_date = request.form.get("due_date", "")

        # Generate receipt number
        count = db.execute("SELECT COUNT(*) as cnt FROM fees").fetchone()["cnt"]
        receipt_no = f"REC-{date.today().strftime('%Y%m')}-{count + 1:04d}"

        status = "paid" if paid_amount >= amount else ("partial" if paid_amount > 0 else "pending")
        paid_date = date.today().isoformat() if paid_amount > 0 else None

        db.execute(
            "INSERT INTO fees (student_id, fee_type, amount, due_date, paid_amount, paid_date, "
            "receipt_no, status, collected_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (student_id, fee_type, amount, due_date, paid_amount, paid_date, receipt_no, status, current_user.id),
        )
        db.commit()
        flash(f"Fee recorded. Receipt: {receipt_no}", "success")
        return redirect(url_for("accountant.fees"))

    # Search for student
    search = request.args.get("search", "").strip()
    students_list = []
    if search:
        students_list = db.execute(
            "SELECT s.*, c.name as class_name FROM students s "
            "JOIN classes c ON s.class_id = c.id "
            "WHERE s.is_active = 1 AND (s.full_name LIKE ? OR s.roll_no LIKE ?) "
            "ORDER BY s.roll_no",
            (f"%{search}%", f"%{search}%"),
        ).fetchall()

    # Recent fee records
    recent_fees = db.execute(
        "SELECT f.*, s.full_name, s.roll_no FROM fees f "
        "JOIN students s ON f.student_id = s.id "
        "ORDER BY f.id DESC LIMIT 20"
    ).fetchall()

    return render_template(
        "accountant/fees.html",
        students=students_list,
        recent_fees=recent_fees,
        search=search,
    )


@accountant_bp.route("/fee-slip/<int:fee_id>")
@login_required
@role_required("accountant", "principal")
def fee_slip(fee_id):
    db = get_db()
    fee = db.execute(
        "SELECT f.*, s.full_name, s.roll_no, s.father_name, c.name as class_name "
        "FROM fees f JOIN students s ON f.student_id = s.id "
        "JOIN classes c ON s.class_id = c.id WHERE f.id = ?",
        (fee_id,),
    ).fetchone()

    if not fee:
        flash("Fee record not found.", "danger")
        return redirect(url_for("accountant.fees"))

    return render_template("accountant/fee_slip.html", fee=fee)


@accountant_bp.route("/pending-fees")
@login_required
@role_required("accountant", "principal")
def pending_fees():
    db = get_db()
    pending = db.execute(
        "SELECT f.*, s.full_name, s.roll_no, s.phone, c.name as class_name "
        "FROM fees f JOIN students s ON f.student_id = s.id "
        "JOIN classes c ON s.class_id = c.id "
        "WHERE f.status != 'paid' ORDER BY f.due_date"
    ).fetchall()

    return render_template("accountant/pending_fees.html", pending=pending)


@accountant_bp.route("/expenditure", methods=["GET", "POST"])
@login_required
@role_required("accountant", "principal")
def expenditure():
    db = get_db()

    if request.method == "POST":
        category = request.form.get("category")
        description = request.form.get("description", "").strip()
        amount = float(request.form.get("amount", 0))
        exp_date = request.form.get("date", date.today().isoformat())

        db.execute(
            "INSERT INTO expenditures (category, description, amount, date, recorded_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (category, description, amount, exp_date, current_user.id),
        )
        db.commit()
        flash("Expenditure recorded.", "success")
        return redirect(url_for("accountant.expenditure"))

    month = request.args.get("month", date.today().strftime("%Y-%m"))
    expenditures = db.execute(
        "SELECT * FROM expenditures WHERE strftime('%Y-%m', date) = ? ORDER BY date DESC",
        (month,),
    ).fetchall()

    # Category totals
    category_totals = db.execute(
        "SELECT category, SUM(amount) as total FROM expenditures "
        "WHERE strftime('%Y-%m', date) = ? GROUP BY category",
        (month,),
    ).fetchall()

    return render_template(
        "accountant/expenditure.html",
        expenditures=expenditures,
        category_totals=category_totals,
        month=month,
    )
