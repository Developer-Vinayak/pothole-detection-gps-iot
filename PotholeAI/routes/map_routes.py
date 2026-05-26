"""routes/map_routes.py"""
from flask import Blueprint, render_template
from core.auth import login_required
map_bp = Blueprint("map", __name__)

@map_bp.route("/map")
@login_required
def index():
    return render_template("map.html")
