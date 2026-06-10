from collections.abc import Iterable

import config
from sender import send_email


def run_mailing(
    recipients: Iterable[str],
    subject: str = config.EMAIL_SUBJECT,
    template: str = config.EMAIL_TEXT,
    sender: str = config.EMAIL_SENDER,
) -> None:
    """Send the configured email body to all recipients."""
    if not template:
        raise ValueError("EMAIL_TEXT must be set in .env")

    for recipient in recipients:
        send_email(recipient=recipient, subject=subject, body=template, sender=sender)
        print(f"Sent email from {sender} to {recipient}")
