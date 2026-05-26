"""routes/about_routes.py"""
from flask import Blueprint, render_template, session
about_bp = Blueprint("about", __name__)

@about_bp.route("/about")
def index():
    return render_template("about.html", logged_in=session.get("logged_in", False))
