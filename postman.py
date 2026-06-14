from collections.abc import Callable, Iterable

import config
from sender import send_email


def run_mailing(
    recipients: Iterable[str],
    subject: str = config.EMAIL_SUBJECT,
    template: str = config.EMAIL_TEXT,
    sender: str = config.EMAIL_SENDER,
    rewrite_body: Callable[[str, int], str] | None = None,
) -> None:
    """Send the configured email body to all recipients."""
    if not template:
        raise ValueError("EMAIL_TEXT must be set in .env")

    for iteration, recipient in enumerate(recipients, start=1):
        body = rewrite_body(template, iteration) if rewrite_body else template
        send_email(recipient=recipient, subject=subject, body=body, sender=sender)
        print(f"Sent email from {sender} to {recipient}")
