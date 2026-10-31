"""Send email with SMTP, or fall back to the dev outbox + console.

Members 1 and 3 both need this: password reset links and invoice/dunning emails.

Usage:
    from app.services.email import send_email

    send_email(db, to="customer@example.com", subject="Your invoice", body=html)
"""

import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.auth.email_outbox import EmailOutbox

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(getattr(settings, "smtp_host", None))


def send_email(db: Session, *, to: str, subject: str, body: str) -> None:
    """Send an email.  In development without SMTP, writes to the outbox table and
    the console so the reset link or invoice email is still visible."""
    if _smtp_configured():
        _send_smtp(to=to, subject=subject, body=body)
    else:
        _send_to_outbox(db, to=to, subject=subject, body=body)


def _send_smtp(*, to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = getattr(settings, "smtp_from", "noreply@brightloop.dev")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body, subtype="html")

    host = settings.smtp_host  # type: ignore[attr-defined]
    port = int(getattr(settings, "smtp_port", 587))
    user = getattr(settings, "smtp_user", None)
    password = getattr(settings, "smtp_password", None)

    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        if port != 25:
            server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(msg)
    logger.info("Email sent to %s: %s", to, subject)


def _send_to_outbox(db: Session, *, to: str, subject: str, body: str) -> None:
    db.add(EmailOutbox(to_email=to, subject=subject, body=body))
    db.flush()
    logger.info("DEV outbox — To: %s | Subject: %s", to, subject)
    # Also print to the container log so the developer doesn't have to query the table.
    print(f"\n{'=' * 60}\n  DEV EMAIL\n  To:      {to}\n  Subject: {subject}\n{'=' * 60}\n{body}\n{'=' * 60}\n")
