"""
Flask web UI for the Local AI Job Search Agent.
Serves the company blacklist management page and jobs list on localhost:5000.
Runs in a daemon thread so it does not block the scheduler.
"""

import logging
from datetime import datetime

from flask import Flask, redirect, render_template, request, url_for

from database import db

logger = logging.getLogger(__name__)

# Flask app instance; debug disabled for production use
app = Flask(__name__, template_folder="templates")
app.config["DEBUG"] = False


@app.route("/")
def index():
    """Redirect root to the blacklist page."""
    return redirect(url_for("blacklist_page"))


@app.route("/blacklist", methods=["GET"])
def blacklist_page():
    """Render the blacklist management page with current blacklist from DB."""
    try:
        companies = db.get_blacklist()
        return render_template("blacklist.html", companies=companies)
    except Exception as e:
        logger.error("blacklist_page failed: %s", e)
        return "Error loading blacklist", 500


@app.route("/blacklist/add", methods=["POST"])
def blacklist_add():
    """Add a company to the blacklist and redirect back to blacklist."""
    company = (request.form.get("company") or "").strip()
    if company:
        try:
            db.add_to_blacklist(company)
        except Exception as e:
            logger.error("blacklist_add failed: %s", e)
    return redirect(url_for("blacklist_page"))


@app.route("/blacklist/remove", methods=["POST"])
def blacklist_remove():
    """Remove a company from the blacklist and redirect back to blacklist."""
    company = (request.form.get("company") or "").strip()
    if company:
        try:
            db.remove_from_blacklist(company)
        except Exception as e:
            logger.error("blacklist_remove failed: %s", e)
    return redirect(url_for("blacklist_page"))


@app.route("/jobs", methods=["GET"])
def jobs_page():
    """Render the jobs list page with all stored jobs sorted by match score."""
    try:
        jobs = db.get_all_jobs(limit=500)
        return render_template("jobs.html", jobs=jobs)
    except Exception as e:
        logger.error("jobs_page failed: %s", e)
        return "Error loading jobs", 500


@app.route("/health")
def health():
    """Return a simple JSON health check."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def run_ui():
    """Start the Flask app on localhost:5000. Intended to be run in a daemon thread."""
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
