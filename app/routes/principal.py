from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app.models import get_db
from app.utils import (
    role_required,
    decrypt_aadhaar,
    mask_aadhaar,
    calculate_kra,
    calculate_salary,
)

principal_bp = Blueprint("principal", __name__)


@principal_bp.route("/dashboard")
@login_required
@role_required("principal")
def dashboard():
    db = get_db()

    total_students = db.execute(
        "SELECT COUNT(*) as cnt FROM students WHERE is_active = 1"
    ).fetchone()["cnt"]
    total_teachers = db.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE role = 'teacher'"
    ).fetchone()["cnt"]
    today = date.today().isoformat()
    present_today = db.execute(
        "SELECT COUNT(*) as cnt FROM student_attendance WHERE date = ? AND status = 'present'",
        (today,),
    ).fetchone()["cnt"]
    total_fees_pending = db.execute(
        "SELECT COALESCE(SUM(amount - paid_amount), 0) as total FROM fees WHERE status != 'paid'"
    ).fetchone()["total"]

    # Recent daily logs
    recent_logs = db.execute(
        "SELECT dl.*, u.full_name as teacher_name, c.name as class_name "
        "FROM daily_logs dl "
        "JOIN users u ON dl.teacher_id = u.id "
        "JOIN classes c ON dl.class_id = c.id "
        "ORDER BY dl.date DESC, dl.created_at DESC LIMIT 10"
    ).fetchall()

    return render_template(
        "principal/dashboard.html",
        total_students=total_students,
        total_teachers=total_teachers,
        present_today=present_today,
        total_fees_pending=total_fees_pending,
        recent_logs=recent_logs,
        today=today,
    )


@principal_bp.route("/manage-users", methods=["GET", "POST"])
@login_required
@role_required("principal")
def manage_users():
    db = get_db()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "teacher")
        full_name = request.form.get("full_name", "").strip()

        existing = db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            flash("Username already exists.", "danger")
        else:
            db.execute(
                "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash(password), role, full_name),
            )
            db.commit()
            flash(f"User '{username}' created as {role}.", "success")
        return redirect(url_for("principal.manage_users"))

    users = db.execute(
        "SELECT id, username, role, full_name, created_at FROM users ORDER BY role, username"
    ).fetchall()

    return render_template("principal/manage_users.html", users=users)


@principal_bp.route("/delete-user/<int:user_id>", methods=["POST"])
@login_required
@role_required("principal")
def delete_user(user_id):
    db = get_db()
    if user_id == current_user.id:
        flash("Cannot delete your own account.", "danger")
    else:
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
        flash("User deleted.", "success")
    return redirect(url_for("principal.manage_users"))


@principal_bp.route("/student-logs")
@login_required
@role_required("principal")
def student_logs():
    db = get_db()
    att_date = request.args.get("date", date.today().isoformat())
    class_id = request.args.get("class_id", "")
    classes = db.execute("SELECT * FROM classes ORDER BY name").fetchall()

    query = (
        "SELECT sa.*, s.full_name, s.roll_no, c.name as class_name "
        "FROM student_attendance sa "
        "JOIN students s ON sa.student_id = s.id "
        "JOIN classes c ON s.class_id = c.id "
        "WHERE sa.date = ?"
    )
    params = [att_date]

    if class_id:
        query += " AND s.class_id = ?"
        params.append(class_id)

    query += " ORDER BY c.name, s.roll_no"
    attendance = db.execute(query, params).fetchall()

    return render_template(
        "principal/student_logs.html",
        attendance=attendance,
        classes=classes,
        att_date=att_date,
        selected_class=class_id,
    )


@principal_bp.route("/salary", methods=["GET", "POST"])
@login_required
@role_required("principal")
def salary():
    db = get_db()
    month = request.args.get("month", date.today().strftime("%m"))
    year = request.args.get("year", str(date.today().year))

    if request.method == "POST":
        teacher_id = request.form.get("teacher_id")
        base_salary = float(request.form.get("base_salary", 0))
        working_days = int(request.form.get("working_days", 0))
        advance = float(request.form.get("advance", 0))
        deductions = float(request.form.get("deductions", 0))
        bonus = float(request.form.get("bonus", 0))
        post_month = request.form.get("month")
        post_year = int(request.form.get("year"))

        # Calculate KRA for teacher
        syllabus_rows = db.execute(
            "SELECT * FROM syllabus WHERE teacher_id = ?", (teacher_id,)
        ).fetchall()
        total_t = sum(r["total_topics"] for r in syllabus_rows) if syllabus_rows else 0
        completed_t = sum(r["completed_topics"] for r in syllabus_rows) if syllabus_rows else 0
        syllabus_pct = (completed_t / total_t * 100) if total_t > 0 else 0

        total_att = db.execute(
            "SELECT COUNT(*) as cnt FROM student_attendance WHERE marked_by = ?",
            (teacher_id,),
        ).fetchone()["cnt"]
        present_att = db.execute(
            "SELECT COUNT(*) as cnt FROM student_attendance WHERE marked_by = ? AND status = 'present'",
            (teacher_id,),
        ).fetchone()["cnt"]
        attendance_pct = (present_att / total_att * 100) if total_att > 0 else 0

        total_hw = db.execute(
            "SELECT COUNT(*) as cnt FROM homework h JOIN daily_logs dl ON h.daily_log_id = dl.id "
            "WHERE dl.teacher_id = ?",
            (teacher_id,),
        ).fetchone()["cnt"]
        done_hw = db.execute(
            "SELECT COUNT(*) as cnt FROM homework h JOIN daily_logs dl ON h.daily_log_id = dl.id "
            "WHERE dl.teacher_id = ? AND h.status = 'done'",
            (teacher_id,),
        ).fetchone()["cnt"]
        homework_pct = (done_hw / total_hw * 100) if total_hw > 0 else 0

        kra_score = calculate_kra(syllabus_pct, attendance_pct, homework_pct)

        # Teacher attendance days
        teacher_att = db.execute(
            "SELECT COUNT(*) as cnt FROM teacher_attendance WHERE teacher_id = ? "
            "AND strftime('%m', date) = ? AND strftime('%Y', date) = ? AND status IN ('present', 'late')",
            (teacher_id, post_month, str(post_year)),
        ).fetchone()["cnt"]

        total_payable = calculate_salary(
            base_salary, kra_score, teacher_att, working_days, advance, deductions, bonus
        )

        db.execute(
            "INSERT OR REPLACE INTO teacher_salary "
            "(teacher_id, month, year, base_salary, kra_score, attendance_days, working_days, "
            "advance, deductions, bonus, total_payable) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                teacher_id, post_month, post_year, base_salary, kra_score,
                teacher_att, working_days, advance, deductions, bonus, total_payable,
            ),
        )
        db.commit()
        flash(f"Salary calculated. Total Payable: Rs. {total_payable}", "success")
        return redirect(url_for("principal.salary", month=post_month, year=post_year))

    teachers = db.execute(
        "SELECT id, username, full_name FROM users WHERE role = 'teacher' ORDER BY full_name"
    ).fetchall()

    salaries = db.execute(
        "SELECT ts.*, u.full_name FROM teacher_salary ts "
        "JOIN users u ON ts.teacher_id = u.id "
        "WHERE ts.month = ? AND ts.year = ? ORDER BY u.full_name",
        (month, year),
    ).fetchall()

    return render_template(
        "principal/salary.html",
        teachers=teachers,
        salaries=salaries,
        month=month,
        year=year,
    )


@principal_bp.route("/approve-salary/<int:salary_id>", methods=["POST"])
@login_required
@role_required("principal")
def approve_salary(salary_id):
    db = get_db()
    db.execute(
        "UPDATE teacher_salary SET approved = 1, approved_by = ?, approved_at = datetime('now') "
        "WHERE id = ?",
        (current_user.id, salary_id),
    )
    db.commit()
    flash("Salary approved.", "success")
    return redirect(url_for("principal.salary"))


@principal_bp.route("/whatsapp-alert/<int:fee_id>")
@login_required
@role_required("principal")
def whatsapp_alert(fee_id):
    db = get_db()
    fee = db.execute(
        "SELECT f.*, s.full_name, s.phone, s.roll_no, c.name as class_name "
        "FROM fees f JOIN students s ON f.student_id = s.id "
        "JOIN classes c ON s.class_id = c.id WHERE f.id = ?",
        (fee_id,),
    ).fetchone()

    if not fee or not fee["phone"]:
        flash("Phone number not available.", "warning")
        return redirect(url_for("accountant.pending_fees"))

    pending = fee["amount"] - fee["paid_amount"]
    message = (
        f"Dear Parent, this is a reminder from Maa Kamala Public School. "
        f"Fee of Rs. {pending:.0f} is pending for {fee['full_name']} "
        f"(Roll: {fee['roll_no']}, Class: {fee['class_name']}). "
        f"Please pay at the earliest. Thank you."
    )

    phone = fee["phone"].replace("+", "").replace(" ", "")
    if not phone.startswith("91"):
        phone = "91" + phone

    wa_url = f"https://wa.me/{phone}?text={message}"
    return redirect(wa_url)


@principal_bp.route("/student-detail/<int:student_id>")
@login_required
@role_required("principal")
def student_detail(student_id):
    db = get_db()
    student = db.execute(
        "SELECT s.*, c.name as class_name FROM students s "
        "JOIN classes c ON s.class_id = c.id WHERE s.id = ?",
        (student_id,),
    ).fetchone()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("principal.dashboard"))

    # Decrypt Aadhaar for principal
    aadhaar_display = ""
    if student["aadhaar_encrypted"]:
        try:
            aadhaar_display = decrypt_aadhaar(student["aadhaar_encrypted"])
        except Exception:
            aadhaar_display = "Decryption Error"

    attendance = db.execute(
        "SELECT * FROM student_attendance WHERE student_id = ? ORDER BY date DESC LIMIT 30",
        (student_id,),
    ).fetchall()

    fees_list = db.execute(
        "SELECT * FROM fees WHERE student_id = ? ORDER BY id DESC",
        (student_id,),
    ).fetchall()

    return render_template(
        "principal/student_detail.html",
        student=student,
        aadhaar=aadhaar_display,
        attendance=attendance,
        fees=fees_list,
    )
