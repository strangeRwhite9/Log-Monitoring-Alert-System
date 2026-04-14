"""Local alert notifier that sends Gmail emails from the user's own machine."""

import argparse
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from app.services.email_service import send_security_alert


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env.notifier")


def build_config():
    """Load notifier settings from the local-only env file."""
    return {
        "source_app_url": os.getenv("SOURCE_APP_URL", "http://127.0.0.1:5000").rstrip("/"),
        "notifier_api_token": os.getenv("NOTIFIER_API_TOKEN", ""),
        "admin_email": os.getenv("ADMIN_EMAIL", "strangerwhite9@gmail.com"),
        "admin_app_password": os.getenv("ADMIN_APP_PASSWORD", ""),
        "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "poll_interval_seconds": int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        "fetch_limit": int(os.getenv("PENDING_ALERT_FETCH_LIMIT", "20")),
        "log_file": Path(os.getenv("NOTIFIER_LOG_FILE", str(BASE_DIR / "notifier.log"))),
    }


def setup_logger(log_file: Path) -> logging.Logger:
    """Write notifier activity to a local log file."""
    logger = logging.getLogger("local_notifier")
    if logger.handlers:
        return logger

    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    return logger


def fetch_pending_alerts(config: dict):
    """Fetch queued alerts from the hosted Flask app."""
    query = urllib.parse.urlencode({"limit": config["fetch_limit"]})
    url = f"{config['source_app_url']}/api/alerts/pending?{query}"
    request = urllib.request.Request(
        url,
        headers={"X-Notifier-Token": config["notifier_api_token"]},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return payload.get("alerts", [])


def acknowledge_alert(config: dict, alert_id: int) -> None:
    """Tell the hosted app that an alert was delivered successfully."""
    url = f"{config['source_app_url']}/api/alerts/{alert_id}/ack"
    request = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Notifier-Token": config["notifier_api_token"],
        },
    )

    with urllib.request.urlopen(request, timeout=20):
        return


def process_alerts(config: dict, logger: logging.Logger) -> int:
    """Send emails for all currently pending alerts and acknowledge them."""
    alerts = fetch_pending_alerts(config)
    delivered = 0

    for alert in alerts:
        sent, error_message = send_security_alert(
            admin_email=config["admin_email"],
            admin_app_password=config["admin_app_password"],
            user_email=alert["user_email"],
            ip_address=alert["ip_address"],
            timestamp=datetime.fromisoformat(alert["attempt_timestamp"]),
            brute_force=alert["brute_force"],
            smtp_server=config["smtp_server"],
            smtp_port=config["smtp_port"],
        )

        if not sent:
            logger.warning(
                "Email send failed for alert_id=%s user_email=%s error=%s",
                alert["id"],
                alert["user_email"],
                error_message,
            )
            continue

        acknowledge_alert(config, alert["id"])
        delivered += 1
        logger.info(
            "Delivered alert_id=%s user_email=%s ip_address=%s",
            alert["id"],
            alert["user_email"],
            alert["ip_address"],
        )

    return delivered


def validate_config(config: dict) -> None:
    """Stop early if the local notifier is missing required secrets."""
    required_values = {
        "SOURCE_APP_URL": config["source_app_url"],
        "NOTIFIER_API_TOKEN": config["notifier_api_token"],
        "ADMIN_EMAIL": config["admin_email"],
        "ADMIN_APP_PASSWORD": config["admin_app_password"],
    }
    missing = [name for name, value in required_values.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required notifier settings: {', '.join(missing)}")


def main() -> None:
    """Run the notifier once or poll in a loop."""
    parser = argparse.ArgumentParser(description="Local Gmail notifier for queued Flask alerts.")
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Keep polling the hosted app for new alerts.",
    )
    args = parser.parse_args()

    config = build_config()
    validate_config(config)
    logger = setup_logger(config["log_file"])

    while True:
        try:
            delivered = process_alerts(config, logger)
            logger.info("Polling cycle complete. delivered=%s", delivered)
        except (OSError, RuntimeError, urllib.error.HTTPError, urllib.error.URLError) as exc:
            logger.error("Notifier cycle failed: %s", exc)

        if not args.poll:
            break

        time.sleep(config["poll_interval_seconds"])


if __name__ == "__main__":
    main()
