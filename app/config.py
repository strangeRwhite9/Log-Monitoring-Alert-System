"""Central configuration for the Flask app."""

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application settings loaded from environment variables."""

    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

    # Beginner-friendly hardcoded test account. Override with env vars if needed.
    VALID_TEST_EMAIL = os.getenv("VALID_TEST_EMAIL", "student@example.com")
    VALID_TEST_PASSWORD = os.getenv("VALID_TEST_PASSWORD", "SecurePass123!")

    # App-level files stored in the project folder unless overridden.
    LOGIN_LOG_FILE = BASE_DIR / "login.log"
    ALERT_DB_FILE = Path(os.getenv("ALERT_DB_FILE", str(BASE_DIR / "alerts.db")))
    NOTIFIER_API_TOKEN = os.getenv("NOTIFIER_API_TOKEN", "")
    PENDING_ALERT_FETCH_LIMIT = int(os.getenv("PENDING_ALERT_FETCH_LIMIT", "20"))

    # Security tuning knobs.
    ATTEMPT_WINDOW_SECONDS = int(os.getenv("ATTEMPT_WINDOW_SECONDS", "900"))
    BRUTE_FORCE_THRESHOLD = int(os.getenv("BRUTE_FORCE_THRESHOLD", "5"))
    ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))
    DELAY_AFTER_FAILURES = int(os.getenv("DELAY_AFTER_FAILURES", "3"))
    LOCKOUT_DELAY_SECONDS = int(os.getenv("LOCKOUT_DELAY_SECONDS", "2"))
