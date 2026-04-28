from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required

from app.models import get_db
from app.utils import role_required

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/", methods=["GET", "POST"])
@login_required
@role_required("principal")
def settings_page():
    db = get_db()

    if request.method == "POST":
        keys = [
            "rfid_enabled", "morning_start", "morning_end",
            "afternoon_start", "afternoon_end", "server_ip", "server_port",
        ]
        for key in keys:
            value = request.form.get(key, "")
            if key == "rfid_enabled":
                value = "1" if request.form.get(key) else "0"
            db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        db.commit()
        flash("Settings saved successfully.", "success")
        return redirect(url_for("settings.settings_page"))

    settings = {}
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    for row in rows:
        settings[row["key"]] = row["value"]

    return render_template("settings/settings.html", settings=settings)
