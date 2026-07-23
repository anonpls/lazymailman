import os
from pathlib import Path


def load_env_file(path: str | os.PathLike[str] = ".env", override: bool = True) -> None:
    """Load simple KEY=VALUE pairs from a .env file without external dependencies."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        value = value.replace("\\n", "\n")

        if override or key not in os.environ:
            os.environ[key] = value


load_env_file(override=True)


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free")

EMAIL_SENDER = os.getenv("EMAIL_SENDER") or os.getenv("GMAIL_EMAIL")
GMAIL_EMAIL = EMAIL_SENDER
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
FALLBACK_EMAIL_SENDER = os.getenv("FALLBACK_EMAIL_SENDER")
FALLBACK_GMAIL_APP_PASSWORD = os.getenv("FALLBACK_GMAIL_APP_PASSWORD") or GMAIL_APP_PASSWORD

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

EMAILS_FILE = os.getenv("EMAILS_FILE", "emails.txt")
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT", "Коммерческое предложение")
EMAIL_TEXT = os.getenv("EMAIL_TEXT", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_TEST_DELAY_SECONDS = float(os.getenv("TELEGRAM_TEST_DELAY_SECONDS", "0"))
EMAIL_SEND_DELAY_SECONDS = float(os.getenv("EMAIL_SEND_DELAY_SECONDS", "0"))
EMAIL_SEND_LOG_FILE = os.getenv("EMAIL_SEND_LOG_FILE", "mailing.log")


def read_recipients(path: str | os.PathLike[str] = EMAILS_FILE) -> list[str]:
    """Read recipients from a txt file; one email address per line."""
    recipients_path = Path(path)
    if not recipients_path.exists():
        raise FileNotFoundError(f"Recipients file not found: {recipients_path}")

    return [
        line.strip()
        for line in recipients_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def remove_recipient(email: str, path: str | os.PathLike[str] = EMAILS_FILE) -> None:
    """Remove a recipient email from the recipients file."""
    recipients_path = Path(path)
    if not recipients_path.exists():
        return

    recipients = read_recipients(recipients_path)
    remaining_recipients = [r for r in recipients if r != email]

    recipients_path.write_text(
        "\n".join(remaining_recipients) + ("\n" if remaining_recipients else ""),
        encoding="utf-8"
    )
