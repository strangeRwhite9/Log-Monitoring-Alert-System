"""SMTP email alert helpers."""

import smtplib
from email.message import EmailMessage


def build_alert_email(
    admin_email: str,
    user_email: str,
    ip_address: str,
    timestamp: str,
    brute_force: bool,
) -> EmailMessage:
    """Create the email sent after a failed login attempt."""
    recipients = [recipient for recipient in dict.fromkeys([admin_email, user_email]) if recipient]

    message = EmailMessage()
    message["Subject"] = "Security Alert: Failed Login Attempt"
    message["From"] = admin_email
    message["To"] = ", ".join(recipients)

    lines = [
        "Warning: A failed login attempt was detected.",
        "",
        f"User email: {user_email}",
        f"IP address: {ip_address}",
        f"Timestamp: {timestamp}",
    ]

    if brute_force:
        lines.extend(["", "Possible brute force attack detected from this IP address."])

    lines.extend(
        [
            "",
            "If this was not you, review your account activity and change credentials.",
        ]
    )

    message.set_content("\n".join(lines))
    return message


def send_security_alert(
    admin_email: str,
    admin_app_password: str,
    user_email: str,
    ip_address: str,
    timestamp,
    brute_force: bool,
    smtp_server: str,
    smtp_port: int,
):
    """Send the security alert email through Gmail SMTP."""
    if not admin_email or not admin_app_password:
        return False, "Missing ADMIN_EMAIL or ADMIN_APP_PASSWORD configuration."

    message = build_alert_email(
        admin_email=admin_email,
        user_email=user_email,
        ip_address=ip_address,
        timestamp=timestamp.isoformat(),
        brute_force=brute_force,
    )

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(admin_email, admin_app_password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        return False, str(exc)

    return True, None
