import os
from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import get_db
from app.utils import role_required, calculate_kra
from config.settings import UPLOAD_DIR

teacher_bp = Blueprint("teacher", __name__)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@teacher_bp.route("/dashboard")
@login_required
@role_required("teacher")
def dashboard():
    db = get_db()
    today = date.today().isoformat()

    # Today's attendance summary for teacher's classes
    classes = db.execute("SELECT * FROM classes ORDER BY name").fetchall()
    today_logs = db.execute(
        "SELECT * FROM daily_logs WHERE teacher_id = ? AND date = ? ORDER BY created_at DESC",
        (current_user.id, today),
    ).fetchall()

    # KRA data
    syllabus_rows = db.execute(
        "SELECT * FROM syllabus WHERE teacher_id = ?",
        (current_user.id,),
    ).fetchall()

    total_topics = sum(r["total_topics"] for r in syllabus_rows) if syllabus_rows else 0
    completed = sum(r["completed_topics"] for r in syllabus_rows) if syllabus_rows else 0
    syllabus_pct = (completed / total_topics * 100) if total_topics > 0 else 0

    return render_template(
        "teacher/dashboard.html",
        classes=classes,
        today_logs=today_logs,
        syllabus_pct=round(syllabus_pct, 1),
        today=today,
    )


@teacher_bp.route("/attendance", methods=["GET", "POST"])
@login_required
@role_required("teacher")
def attendance():
    db = get_db()
    classes = db.execute("SELECT * FROM classes ORDER BY name").fetchall()
    att_date = request.args.get("date", date.today().isoformat())
    class_id = request.args.get("class_id", "")

    students = []
    existing_attendance = {}

    if class_id:
        students = db.execute(
            "SELECT * FROM students WHERE class_id = ? AND is_active = 1 ORDER BY roll_no",
            (class_id,),
        ).fetchall()

        rows = db.execute(
            "SELECT student_id, status FROM student_attendance WHERE date = ? AND student_id IN "
            "(SELECT id FROM students WHERE class_id = ?)",
            (att_date, class_id),
        ).fetchall()
        existing_attendance = {r["student_id"]: r["status"] for r in rows}

    if request.method == "POST":
        method = request.form.get("method", "manual")
        post_class_id = request.form.get("class_id")
        post_date = request.form.get("date", att_date)

        post_students = db.execute(
            "SELECT id FROM students WHERE class_id = ? AND is_active = 1",
            (post_class_id,),
        ).fetchall()

        for s in post_students:
            status = request.form.get(f"status_{s['id']}", "absent")
            db.execute(
                "INSERT OR REPLACE INTO student_attendance (student_id, date, status, method, marked_by) "
                "VALUES (?, ?, ?, ?, ?)",
                (s["id"], post_date, status, method, current_user.id),
            )
        db.commit()
        flash("Attendance saved successfully.", "success")
        return redirect(
            url_for("teacher.attendance", class_id=post_class_id, date=post_date)
        )

    return render_template(
        "teacher/attendance.html",
        classes=classes,
        students=students,
        existing=existing_attendance,
        selected_class=class_id,
        att_date=att_date,
    )


@teacher_bp.route("/daily-log", methods=["GET", "POST"])
@login_required
@role_required("teacher")
def daily_log():
    db = get_db()
    classes = db.execute("SELECT * FROM classes ORDER BY name").fetchall()

    if request.method == "POST":
        class_id = request.form.get("class_id")
        subject = request.form.get("subject", "").strip()
        topic = request.form.get("topic", "").strip()
        notes = request.form.get("notes", "").strip()
        log_date = request.form.get("date", date.today().isoformat())

        image_path = None
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and _allowed_file(file.filename):
                filename = secure_filename(f"{current_user.id}_{log_date}_{file.filename}")
                hw_dir = os.path.join(UPLOAD_DIR, "homework")
                os.makedirs(hw_dir, exist_ok=True)
                file.save(os.path.join(hw_dir, filename))
                image_path = f"uploads/homework/{filename}"

        db.execute(
            "INSERT INTO daily_logs (teacher_id, date, class_id, subject, topic, notes, image_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (current_user.id, log_date, class_id, subject, topic, notes, image_path),
        )
        db.commit()
        flash("Daily log saved.", "success")
        return redirect(url_for("teacher.daily_log"))

    logs = db.execute(
        "SELECT dl.*, c.name as class_name FROM daily_logs dl "
        "JOIN classes c ON dl.class_id = c.id "
        "WHERE dl.teacher_id = ? ORDER BY dl.date DESC, dl.created_at DESC LIMIT 30",
        (current_user.id,),
    ).fetchall()

    return render_template("teacher/daily_log.html", classes=classes, logs=logs)


@teacher_bp.route("/homework/<int:log_id>", methods=["GET", "POST"])
@login_required
@role_required("teacher")
def homework(log_id):
    db = get_db()
    log = db.execute(
        "SELECT dl.*, c.name as class_name FROM daily_logs dl "
        "JOIN classes c ON dl.class_id = c.id WHERE dl.id = ?",
        (log_id,),
    ).fetchone()

    if not log:
        flash("Log not found.", "danger")
        return redirect(url_for("teacher.daily_log"))

    students = db.execute(
        "SELECT * FROM students WHERE class_id = ? AND is_active = 1 ORDER BY roll_no",
        (log["class_id"],),
    ).fetchall()

    existing = {}
    rows = db.execute(
        "SELECT student_id, status, remarks FROM homework WHERE daily_log_id = ?",
        (log_id,),
    ).fetchall()
    existing = {r["student_id"]: {"status": r["status"], "remarks": r["remarks"]} for r in rows}

    if request.method == "POST":
        for s in students:
            status = request.form.get(f"hw_{s['id']}", "not_done")
            remarks = request.form.get(f"remarks_{s['id']}", "")
            db.execute(
                "INSERT OR REPLACE INTO homework (daily_log_id, student_id, status, remarks) "
                "VALUES (?, ?, ?, ?)",
                (log_id, s["id"], status, remarks),
            )
        db.commit()
        flash("Homework status updated.", "success")
        return redirect(url_for("teacher.homework", log_id=log_id))

    return render_template(
        "teacher/homework.html", log=log, students=students, existing=existing
    )


@teacher_bp.route("/kra")
@login_required
@role_required("teacher")
def kra():
    db = get_db()

    # Syllabus completion
    syllabus_rows = db.execute(
        "SELECT * FROM syllabus WHERE teacher_id = ?",
        (current_user.id,),
    ).fetchall()
    total_topics = sum(r["total_topics"] for r in syllabus_rows) if syllabus_rows else 0
    completed = sum(r["completed_topics"] for r in syllabus_rows) if syllabus_rows else 0
    syllabus_pct = (completed / total_topics * 100) if total_topics > 0 else 0

    # Student attendance percentage (all classes taught)
    total_att = db.execute(
        "SELECT COUNT(*) as cnt FROM student_attendance WHERE marked_by = ?",
        (current_user.id,),
    ).fetchone()["cnt"]
    present_att = db.execute(
        "SELECT COUNT(*) as cnt FROM student_attendance WHERE marked_by = ? AND status = 'present'",
        (current_user.id,),
    ).fetchone()["cnt"]
    attendance_pct = (present_att / total_att * 100) if total_att > 0 else 0

    # Homework compliance
    total_hw = db.execute(
        "SELECT COUNT(*) as cnt FROM homework h JOIN daily_logs dl ON h.daily_log_id = dl.id "
        "WHERE dl.teacher_id = ?",
        (current_user.id,),
    ).fetchone()["cnt"]
    done_hw = db.execute(
        "SELECT COUNT(*) as cnt FROM homework h JOIN daily_logs dl ON h.daily_log_id = dl.id "
        "WHERE dl.teacher_id = ? AND h.status = 'done'",
        (current_user.id,),
    ).fetchone()["cnt"]
    homework_pct = (done_hw / total_hw * 100) if total_hw > 0 else 0

    kra_score = calculate_kra(syllabus_pct, attendance_pct, homework_pct)

    return render_template(
        "teacher/kra.html",
        syllabus_pct=round(syllabus_pct, 1),
        attendance_pct=round(attendance_pct, 1),
        homework_pct=round(homework_pct, 1),
        kra_score=kra_score,
        syllabus_rows=syllabus_rows,
    )


@teacher_bp.route("/syllabus", methods=["GET", "POST"])
@login_required
@role_required("teacher")
def syllabus():
    db = get_db()
    classes = db.execute("SELECT * FROM classes ORDER BY name").fetchall()

    if request.method == "POST":
        class_id = request.form.get("class_id")
        subject = request.form.get("subject", "").strip()
        total_topics = int(request.form.get("total_topics", 0))
        completed_topics = int(request.form.get("completed_topics", 0))

        existing = db.execute(
            "SELECT id FROM syllabus WHERE teacher_id = ? AND class_id = ? AND subject = ?",
            (current_user.id, class_id, subject),
        ).fetchone()

        if existing:
            db.execute(
                "UPDATE syllabus SET total_topics = ?, completed_topics = ? WHERE id = ?",
                (total_topics, completed_topics, existing["id"]),
            )
        else:
            db.execute(
                "INSERT INTO syllabus (class_id, subject, total_topics, completed_topics, teacher_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (class_id, subject, total_topics, completed_topics, current_user.id),
            )
        db.commit()
        flash("Syllabus updated.", "success")
        return redirect(url_for("teacher.syllabus"))

    syllabus_rows = db.execute(
        "SELECT s.*, c.name as class_name FROM syllabus s "
        "JOIN classes c ON s.class_id = c.id WHERE s.teacher_id = ? ORDER BY c.name, s.subject",
        (current_user.id,),
    ).fetchall()

    return render_template("teacher/syllabus.html", classes=classes, syllabus_rows=syllabus_rows)
