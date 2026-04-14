"""Web routes for the login demo."""

import hmac
import time
from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .services.auth_service import is_valid_login, normalize_email
from .services.alert_store import fetch_pending_alerts, mark_alert_sent, queue_alert
from .services.logging_service import log_failed_attempt
from .services.security_service import attempt_tracker, get_client_ip


main_bp = Blueprint("main", __name__)


def require_notifier_token():
    """Protect local-notifier API endpoints with a shared secret token."""
    expected = current_app.config["NOTIFIER_API_TOKEN"]
    provided = request.headers.get("X-Notifier-Token", "")

    if not expected:
        abort(503, description="Notifier API token is not configured.")

    if not hmac.compare_digest(provided, expected):
        abort(403, description="Invalid notifier token.")


@main_bp.route("/", methods=["GET", "POST"])
def login():
    """Render the login form and process login attempts."""
    entered_email = ""

    if request.method == "POST":
        entered_email = normalize_email(request.form.get("email", ""))
        password = request.form.get("password", "")
        client_ip = get_client_ip(request)
        event_time = datetime.now(timezone.utc)
        window_seconds = current_app.config["ATTEMPT_WINDOW_SECONDS"]

        # Slow down repeated failures from the same IP to reduce brute-force speed.
        existing_failures = attempt_tracker.get_failure_count(
            client_ip, event_time, window_seconds
        )
        if existing_failures >= current_app.config["DELAY_AFTER_FAILURES"]:
            time.sleep(current_app.config["LOCKOUT_DELAY_SECONDS"])

        if is_valid_login(entered_email, password, current_app.config):
            attempt_tracker.reset_failures(client_ip)
            session["authenticated_email"] = entered_email
            session["last_login_ip"] = client_ip
            flash("Login successful.", "success")
            return redirect(url_for("main.success"))

        failure_count = attempt_tracker.record_failure(
            client_ip, event_time, window_seconds
        )
        log_failed_attempt(
            current_app.config["LOGIN_LOG_FILE"],
            entered_email,
            client_ip,
            event_time,
        )

        should_alert, cooldown_left = attempt_tracker.should_send_alert(
            client_ip,
            event_time,
            current_app.config["ALERT_COOLDOWN_SECONDS"],
        )

        if should_alert:
            brute_force = failure_count > current_app.config["BRUTE_FORCE_THRESHOLD"]
            queue_alert(
                db_file=current_app.config["ALERT_DB_FILE"],
                user_email=entered_email,
                ip_address=client_ip,
                attempt_timestamp=event_time,
                brute_force=brute_force,
                failure_count=failure_count,
            )
        else:
            current_app.logger.info(
                "Alert suppressed by cooldown for ip=%s email=%s seconds_left=%s",
                client_ip,
                entered_email,
                cooldown_left,
            )

        flash("Invalid email or password. This attempt was recorded for review.", "error")

    return render_template("login.html", entered_email=entered_email)


@main_bp.route("/success", methods=["GET"])
def success():
    """Show a simple success page after a valid login."""
    email = session.get("authenticated_email")
    ip_address = session.get("last_login_ip")

    if not email:
        flash("Please log in first.", "error")
        return redirect(url_for("main.login"))

    return render_template("success.html", email=email, ip_address=ip_address)


@main_bp.route("/api/alerts/pending", methods=["GET"])
def pending_alerts():
    """Return queued alerts for the local notifier worker."""
    require_notifier_token()

    limit = request.args.get("limit", type=int) or current_app.config["PENDING_ALERT_FETCH_LIMIT"]
    limit = max(1, min(limit, 100))
    alerts = fetch_pending_alerts(current_app.config["ALERT_DB_FILE"], limit)
    return jsonify({"alerts": alerts})


@main_bp.route("/api/alerts/<int:alert_id>/ack", methods=["POST"])
def acknowledge_alert(alert_id: int):
    """Mark an alert as sent after the local notifier emails it."""
    require_notifier_token()

    sent_at = datetime.now(timezone.utc)
    mark_alert_sent(current_app.config["ALERT_DB_FILE"], alert_id, sent_at)
    return jsonify({"status": "ok", "alert_id": alert_id, "sent_at": sent_at.isoformat()})
