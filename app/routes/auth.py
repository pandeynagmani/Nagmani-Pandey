from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import get_db, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == "principal":
            return redirect(url_for("principal.dashboard"))
        elif current_user.role == "teacher":
            return redirect(url_for("teacher.dashboard"))
        elif current_user.role == "accountant":
            return redirect(url_for("accountant.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        row = db.execute(
            "SELECT id, username, password_hash, role, full_name FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if row and check_password_hash(row["password_hash"], password):
            user = User(row["id"], row["username"], row["role"], row["full_name"])
            login_user(user)
            flash(f"Welcome, {user.full_name}!", "success")
            return redirect(url_for("auth.index"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")

        db = get_db()
        row = db.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (current_user.id,),
        ).fetchone()

        if not check_password_hash(row["password_hash"], current_pw):
            flash("Current password is incorrect.", "danger")
        elif new_pw != confirm_pw:
            flash("New passwords do not match.", "danger")
        elif len(new_pw) < 4:
            flash("Password must be at least 4 characters.", "danger")
        else:
            db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(new_pw), current_user.id),
            )
            db.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("auth.index"))

    return render_template("auth/change_password.html")
