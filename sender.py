import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


def send_email(
    recipient: str,
    subject: str,
    body: str,
    sender: str = config.EMAIL_SENDER,
) -> None:
    """Send a plain-text email through the configured SMTP server."""
    if not sender:
        raise ValueError("EMAIL_SENDER or GMAIL_EMAIL must be set in .env")
    if not config.GMAIL_APP_PASSWORD:
        raise ValueError("GMAIL_APP_PASSWORD must be set in .env")

    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
        server.starttls()
        server.login(sender, config.GMAIL_APP_PASSWORD)
        server.sendmail(sender, recipient, message.as_string())
