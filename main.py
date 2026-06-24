import argparse
import importlib.util
from pathlib import Path

import config
from postman import run_mailing
from rewriter import rewrite_email


TG_TEST_SCRIPT = Path(__file__).parent / "tests" / "tg-test.py"


def load_tg_test_module():
    spec = importlib.util.spec_from_file_location("tg_test", TG_TEST_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Telegram test module: {TG_TEST_SCRIPT}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lazy Mailman mailing runner")
    parser.add_argument(
        "--test",
        action="store_true",
        help="simulate mailing by sending preview messages to Telegram instead of email",
    )
    parser.add_argument(
        "--emails-file",
        default=config.EMAILS_FILE,
        help="path to txt file with one recipient email per line",
    )
    parser.add_argument(
        "--rewriter",
        action="store_true",
        help="rewrite the email body through OpenRouter separately for every recipient",
    )
    parser.add_argument(
        "--send-delay",
        type=float,
        default=config.EMAIL_SEND_DELAY_SECONDS,
        help="pause between real email sends in seconds",
    )
    parser.add_argument(
        "--fallback-sender",
        default=config.FALLBACK_EMAIL_SENDER,
        help="fallback sender email used when the primary SMTP send fails",
    )
    parser.add_argument(
        "--log-file",
        default=config.EMAIL_SEND_LOG_FILE,
        help="path to the mailing result log file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    recipients = config.read_recipients(args.emails_file)

    rewrite_body = rewrite_email if args.rewriter else None

    if args.test:
        tg_test = load_tg_test_module()
        tg_test.run_test_mailing(
            recipients=recipients,
            sender=config.EMAIL_SENDER,
            subject=config.EMAIL_SUBJECT,
            body=config.EMAIL_TEXT,
            rewrite_body=rewrite_body,
        )
        return

    run_mailing(
        recipients=recipients,
        subject=config.EMAIL_SUBJECT,
        template=config.EMAIL_TEXT,
        sender=config.EMAIL_SENDER,
        rewrite_body=rewrite_body,
        delay_seconds=args.send_delay,
        fallback_sender=args.fallback_sender,
        log_file=args.log_file,
        emails_file=args.emails_file,
    )


if __name__ == "__main__":
    main()
