import logging
import time
from collections.abc import Callable, Iterable
from pathlib import Path

import config
from sender import EmailSendResult, send_email
from config import remove_recipient


SPAM_CHECK_STATUS = "not_supported_by_smtp"


def configure_mailing_logger(log_file: str = config.EMAIL_SEND_LOG_FILE) -> logging.Logger:
    """Create a logger for per-recipient mailing results."""
    logger = logging.getLogger("lazymailman.mailing")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path = Path(log_file)
    if log_path.parent != Path("."):
        log_path.parent.mkdir(parents=True, exist_ok=True)

    wanted_path = str(log_path.resolve())
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == wanted_path:
            return logger

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(file_handler)
    return logger


def log_send_result(
    logger: logging.Logger,
    result: EmailSendResult,
    attempt: str,
    final: bool,
) -> None:
    """Log success or failure for one SMTP send attempt."""
    status = "success" if result.success else "failure"
    message = (
        "email_send "
        f"status={status} attempt={attempt} final={final} "
        f"sender={result.sender} recipient={result.recipient} "
        f"spam_check={SPAM_CHECK_STATUS}"
    )
    if result.error:
        message = f"{message} error={result.error!r}"
    if result.smtp_response:
        message = f"{message} smtp_response={result.smtp_response!r}"

    if result.success:
        logger.info(message)
    else:
        logger.error(message)


def run_mailing(
    recipients: Iterable[str],
    subject: str = config.EMAIL_SUBJECT,
    template: str = config.EMAIL_TEXT,
    sender: str = config.EMAIL_SENDER,
    rewrite_body: Callable[[str, int], str] | None = None,
    delay_seconds: float = config.EMAIL_SEND_DELAY_SECONDS,
    fallback_sender: str | None = config.FALLBACK_EMAIL_SENDER,
    fallback_password: str | None = config.FALLBACK_GMAIL_APP_PASSWORD,
    log_file: str = config.EMAIL_SEND_LOG_FILE,
    emails_file: str = config.EMAILS_FILE,
) -> None:
    """Send the configured email body to all recipients."""
    if not template:
        raise ValueError("EMAIL_TEXT must be set in .env")
    if delay_seconds < 0:
        raise ValueError("EMAIL_SEND_DELAY_SECONDS cannot be negative")

    logger = configure_mailing_logger(log_file)
    recipient_list = list(recipients)

    for iteration, recipient in enumerate(recipient_list, start=1):
        body = rewrite_body(template, iteration) if rewrite_body else template
        result = send_email(recipient=recipient, subject=subject, body=body, sender=sender)

        if result.success:
            log_send_result(logger, result, attempt="primary", final=True)
            print(f"Sent email from {sender} to {recipient}")
            remove_recipient(recipient, emails_file)
        else:
            can_use_fallback = bool(fallback_sender and fallback_sender != sender)
            log_send_result(logger, result, attempt="primary", final=not can_use_fallback)
            print(f"Failed to send email from {sender} to {recipient}: {result.error}")

            if can_use_fallback:
                fallback_result = send_email(
                    recipient=recipient,
                    subject=subject,
                    body=body,
                    sender=fallback_sender,
                    password=fallback_password,
                )
                log_send_result(logger, fallback_result, attempt="fallback", final=True)
                if fallback_result.success:
                    print(f"Sent email from fallback {fallback_sender} to {recipient}")
                    remove_recipient(recipient, emails_file)
                else:
                    print(
                        "Failed to send email from fallback "
                        f"{fallback_sender} to {recipient}: {fallback_result.error}"
                    )

        if delay_seconds and iteration < len(recipient_list):
            time.sleep(delay_seconds)
