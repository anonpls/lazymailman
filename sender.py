import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


@dataclass(frozen=True)
class EmailSendResult:
    """Result of a single SMTP send attempt."""

    success: bool
    sender: str
    recipient: str
    error: str | None = None
    smtp_response: dict[str, tuple[int, bytes]] | None = None


def send_email(
    recipient: str,
    subject: str,
    body: str,
    sender: str = config.EMAIL_SENDER,
    password: str | None = None,
) -> EmailSendResult:
    """Send a plain-text email through the configured SMTP server."""
    if not sender:
        raise ValueError("EMAIL_SENDER or GMAIL_EMAIL must be set in .env")

    smtp_password = password or config.GMAIL_APP_PASSWORD
    if not smtp_password:
        raise ValueError("GMAIL_APP_PASSWORD must be set in .env")

    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(sender, smtp_password)
            smtp_response = server.sendmail(sender, recipient, message.as_string())
    except Exception as exc:
        return EmailSendResult(
            success=False,
            sender=sender,
            recipient=recipient,
            error=f"{type(exc).__name__}: {exc}",
        )

    if smtp_response:
        return EmailSendResult(
            success=False,
            sender=sender,
            recipient=recipient,
            error="SMTP rejected one or more recipients",
            smtp_response=smtp_response,
        )

    return EmailSendResult(success=True, sender=sender, recipient=recipient)
