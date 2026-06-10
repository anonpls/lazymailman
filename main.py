import smtplib
import requests
import time
import config
from postman import run_mailing

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


OPENROUTER_API_KEY = config.OPENROUTER_API_KEY

GMAIL_EMAIL = config.GMAIL_EMAIL
GMAIL_APP_PASSWORD = config.GMAIL_APP_PASSWORD

SMTP_SERVER = config.SMTP_SERVER
SMTP_PORT = config.SMTP_PORT

if __name__ == "__main__":
    emails = [
        "user1@example.com",
        "user2@example.com",
        "user3@example.com"
    ]

    subject = "Коммерческое предложение"

    template = """
Здравствуйте!

Хотим предложить вам сотрудничество в сфере разработки программного обеспечения.

Если вам интересно обсудить детали, ответьте на это письмо.

С уважением.
"""

    run_mailing(emails, subject, template)