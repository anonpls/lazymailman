import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config


TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def build_test_message(sender: str, recipient: str, subject: str, body: str) -> str:
    return (
        "🧪 Тестовая рассылка\n"
        f"Почта отправитель: {sender}\n"
        f"Почта получатель: {recipient}\n"
        f"Тема: {subject}\n\n"
        f"Текст письма:\n{body}"
    )


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        TELEGRAM_API_URL.format(token=bot_token),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API request failed: {details}") from error


def run_test_mailing(
    recipients: Iterable[str],
    sender: str = config.EMAIL_SENDER,
    subject: str = config.EMAIL_SUBJECT,
    body: str = config.EMAIL_TEXT,
    bot_token: str = config.TELEGRAM_BOT_TOKEN,
    chat_id: str = config.TELEGRAM_CHAT_ID,
    delay_seconds: float = config.TELEGRAM_TEST_DELAY_SECONDS,
) -> None:
    if not sender:
        raise ValueError("EMAIL_SENDER or GMAIL_EMAIL must be set in .env")
    if not body:
        raise ValueError("EMAIL_TEXT must be set in .env")
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN must be set in .env")
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID must be set in .env")

    for recipient in recipients:
        message = build_test_message(sender, recipient, subject, body)
        send_telegram_message(bot_token, chat_id, message)
        print(f"Sent Telegram test message for {sender} -> {recipient}")
        if delay_seconds > 0:
            time.sleep(delay_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send Telegram messages for a test mailing")
    parser.add_argument(
        "--emails-file",
        default=config.EMAILS_FILE,
        help="path to txt file with one recipient email per line",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_test_mailing(config.read_recipients(args.emails_file))


if __name__ == "__main__":
    main()
