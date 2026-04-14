"""Failed-login file logging."""

import logging


FAILED_LOGIN_LOGGER_NAME = "failed_login_logger"


def get_failed_login_logger(log_file) -> logging.Logger:
    """Create one dedicated logger for the login.log file."""
    logger = logging.getLogger(FAILED_LOGIN_LOGGER_NAME)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(file_handler)
    return logger


def log_failed_attempt(log_file, email: str, ip_address: str, timestamp) -> None:
    """Write a structured failed-login entry to login.log."""
    logger = get_failed_login_logger(log_file)
    logger.info(
        "email=%s | ip_address=%s | timestamp=%s",
        email,
        ip_address,
        timestamp.isoformat(),
    )
