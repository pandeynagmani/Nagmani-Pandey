from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.models import get_db
from app.utils import role_required, mask_aadhaar, decrypt_aadhaar

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/id-card/<int:student_id>")
@login_required
@role_required("accountant", "principal")
def id_card(student_id):
    db = get_db()
    student = db.execute(
        "SELECT s.*, c.name as class_name FROM students s "
        "JOIN classes c ON s.class_id = c.id WHERE s.id = ?",
        (student_id,),
    ).fetchone()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("accountant.students"))

    return render_template("documents/id_card.html", student=student)


@documents_bp.route("/admit-card/<int:student_id>")
@login_required
@role_required("accountant", "principal")
def admit_card(student_id):
    db = get_db()
    student = db.execute(
        "SELECT s.*, c.name as class_name FROM students s "
        "JOIN classes c ON s.class_id = c.id WHERE s.id = ?",
        (student_id,),
    ).fetchone()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("accountant.students"))

    exam_name = request.args.get("exam", "Annual Examination 2025-26")
    subjects = db.execute(
        "SELECT DISTINCT subject FROM syllabus WHERE class_id = ?",
        (student["class_id"],),
    ).fetchall()

    return render_template(
        "documents/admit_card.html",
        student=student,
        exam_name=exam_name,
        subjects=subjects,
    )


@documents_bp.route("/report-card/<int:student_id>")
@login_required
@role_required("accountant", "principal")
def report_card(student_id):
    db = get_db()
    student = db.execute(
        "SELECT s.*, c.name as class_name FROM students s "
        "JOIN classes c ON s.class_id = c.id WHERE s.id = ?",
        (student_id,),
    ).fetchone()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("accountant.students"))

    exam_name = request.args.get("exam", "Annual Examination 2025-26")
    results = db.execute(
        "SELECT * FROM exam_results WHERE student_id = ? AND exam_name = ? ORDER BY subject",
        (student_id, exam_name),
    ).fetchall()

    total_max = sum(r["max_marks"] for r in results) if results else 0
    total_obtained = sum(r["obtained_marks"] for r in results) if results else 0
    percentage = (total_obtained / total_max * 100) if total_max > 0 else 0

    # Attendance summary
    total_att = db.execute(
        "SELECT COUNT(*) as cnt FROM student_attendance WHERE student_id = ?",
        (student_id,),
    ).fetchone()["cnt"]
    present_att = db.execute(
        "SELECT COUNT(*) as cnt FROM student_attendance WHERE student_id = ? AND status = 'present'",
        (student_id,),
    ).fetchone()["cnt"]

    return render_template(
        "documents/report_card.html",
        student=student,
        exam_name=exam_name,
        results=results,
        total_max=total_max,
        total_obtained=total_obtained,
        percentage=round(percentage, 1),
        total_att=total_att,
        present_att=present_att,
    )
