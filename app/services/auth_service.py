"""Authentication helpers."""


def normalize_email(email: str) -> str:
    """Normalize user input so comparisons are consistent."""
    return email.strip().lower()


def is_valid_login(email: str, password: str, config: dict) -> bool:
    """Check the submitted credentials against the hardcoded test user."""
    return (
        normalize_email(email) == normalize_email(config["VALID_TEST_EMAIL"])
        and password == config["VALID_TEST_PASSWORD"]
    )
