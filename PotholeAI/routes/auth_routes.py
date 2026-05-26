"""
routes/auth_routes.py — Login / Logout
"""

from flask import Blueprint, request, session, redirect, url_for, render_template
from config.settings import ADMIN_ID, ADMIN_PASSWORD

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard.index"))
    error = None
    if request.method == "POST":
        admin_id = request.form.get("admin_id", "").strip()
        password = request.form.get("password", "").strip()
        if admin_id == ADMIN_ID and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            session["admin_id"]  = admin_id
            print(f"[AUTH] Admin '{admin_id}' logged in.")
            return redirect(url_for("dashboard.index"))
        error = "Invalid Admin ID or password. Please try again."
        print(f"[AUTH] Failed login attempt — ID='{admin_id}'")
    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
