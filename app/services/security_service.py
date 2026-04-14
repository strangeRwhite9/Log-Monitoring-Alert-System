"""In-memory security tracking utilities."""

from collections import defaultdict
from datetime import timedelta


class AttemptTracker:
    """Track failed logins and alert cooldowns for the current app process."""

    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.alert_cooldowns = {}

    def _trim_attempts(self, ip_address: str, now, window_seconds: int):
        """Keep only recent failures inside the active tracking window."""
        cutoff = now - timedelta(seconds=window_seconds)
        attempts = [attempt for attempt in self.failed_attempts[ip_address] if attempt >= cutoff]
        self.failed_attempts[ip_address] = attempts
        return attempts

    def get_failure_count(self, ip_address: str, now, window_seconds: int) -> int:
        """Return the current failure count for an IP in the active window."""
        return len(self._trim_attempts(ip_address, now, window_seconds))

    def record_failure(self, ip_address: str, now, window_seconds: int) -> int:
        """Store a new failed attempt and return the updated count."""
        attempts = self._trim_attempts(ip_address, now, window_seconds)
        attempts.append(now)
        self.failed_attempts[ip_address] = attempts
        return len(attempts)

    def reset_failures(self, ip_address: str) -> None:
        """Clear failed-attempt history after a successful login."""
        self.failed_attempts.pop(ip_address, None)

    def should_send_alert(
        self,
        ip_address: str,
        now,
        cooldown_seconds: int,
    ):
        """Return whether an alert can be sent or is still on cooldown."""
        # Cool down by source IP so one attacker cannot spam alerts rapidly.
        cooldown_key = ip_address
        last_sent = self.alert_cooldowns.get(cooldown_key)

        if last_sent is None:
            self.alert_cooldowns[cooldown_key] = now
            return True, 0

        elapsed = (now - last_sent).total_seconds()
        if elapsed < cooldown_seconds:
            return False, int(cooldown_seconds - elapsed)

        self.alert_cooldowns[cooldown_key] = now
        return True, 0


attempt_tracker = AttemptTracker()


def get_client_ip(request) -> str:
    """Read the best client IP available, including proxy headers."""
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    return request.remote_addr or "unknown"
