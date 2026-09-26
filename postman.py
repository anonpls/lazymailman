import logging
import time
from datetime import datetime, time as datetime_time, timedelta
from collections.abc import Callable, Iterable
from pathlib import Path

import config
from sender import EmailSendResult, send_email
from config import remove_recipient


SPAM_CHECK_STATUS = "not_supported_by_smtp"
TIME_FORMAT = "%H:%M"


def parse_active_time(value: str | None, variable_name: str) -> datetime_time | None:
    """Parse HH:MM mailing activity boundary from .env."""
    if not value:
        return None

    try:
        return datetime.strptime(value, TIME_FORMAT).time()
    except ValueError as exc:
        raise ValueError(f"{variable_name} must use HH:MM format") from exc


def is_within_active_period(
    current_time: datetime_time,
    active_from: datetime_time | None,
    active_to: datetime_time | None,
) -> bool:
    """Return whether current local system time is inside the configured mailing window."""
    if active_from is None and active_to is None:
        return True
    if active_from is None:
        return current_time <= active_to
    if active_to is None:
        return current_time >= active_from
    if active_from <= active_to:
        return active_from <= current_time <= active_to
    return current_time >= active_from or current_time <= active_to


def seconds_until_active_period(
    now: datetime,
    active_from: datetime_time | None,
    active_to: datetime_time | None,
) -> float:
    """Return seconds until the next allowed send time using local system time."""
    if is_within_active_period(now.time(), active_from, active_to):
        return 0
    if active_from is None:
        next_start = datetime.combine(now.date() + timedelta(days=1), datetime_time.min)
    else:
        next_start = datetime.combine(now.date(), active_from)
        if next_start <= now:
            next_start += timedelta(days=1)
    return (next_start - now).total_seconds()


def wait_for_active_period(
    active_from: datetime_time | None,
    active_to: datetime_time | None,
    sleep: Callable[[float], None] = time.sleep,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    """Pause mailing until local system time enters the configured activity window."""
    if active_from is None and active_to is None:
        return

    wait_seconds = seconds_until_active_period(datetime.now(), active_from, active_to)
    if wait_seconds > 0:
        print(f"Mailing is outside the active period; waiting {wait_seconds:.0f} seconds")
        remaining = wait_seconds
        while remaining > 0 and not (should_stop and should_stop()):
            pause = min(remaining, 0.25)
            sleep(pause)
            remaining -= pause


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
    primary_password: str | None = None,
    fallback_sender: str | None = config.FALLBACK_EMAIL_SENDER,
    fallback_password: str | None = config.FALLBACK_GMAIL_APP_PASSWORD,
    log_file: str = config.EMAIL_SEND_LOG_FILE,
    emails_file: str = config.EMAILS_FILE,
    active_from: str | None = config.MAILING_ACTIVE_FROM,
    active_to: str | None = config.MAILING_ACTIVE_TO,
    should_stop: Callable[[], bool] | None = None,
    on_event: Callable[[str, str, str], None] | None = None,
) -> None:
    """Send the configured email body to all recipients."""
    if not template:
        raise ValueError("EMAIL_TEXT must be set in .env")
    if delay_seconds < 0:
        raise ValueError("EMAIL_SEND_DELAY_SECONDS cannot be negative")

    active_from_time = parse_active_time(active_from, "MAILING_ACTIVE_FROM")
    active_to_time = parse_active_time(active_to, "MAILING_ACTIVE_TO")

    logger = configure_mailing_logger(log_file)
    recipient_list = list(recipients)

    for iteration, recipient in enumerate(recipient_list, start=1):
        if should_stop and should_stop():
            break
        if on_event:
            on_event("sending", recipient)
        wait_for_active_period(active_from_time, active_to_time, should_stop=should_stop)
        if should_stop and should_stop():
            break
        body = rewrite_body(template, iteration) if rewrite_body else template
        result = send_email(recipient=recipient, subject=subject, body=body, sender=sender, password=primary_password)

        if result.success:
            log_send_result(logger, result, attempt="primary", final=True)
            print(f"Sent email from {sender} to {recipient}")
            if on_event:
                on_event("success", recipient)
            remove_recipient(recipient, emails_file)
        else:
            can_use_fallback = bool(fallback_sender and fallback_sender != sender)
            log_send_result(logger, result, attempt="primary", final=not can_use_fallback)
            print(f"Failed to send email from {sender} to {recipient}: {result.error}")
            if on_event:
                on_event("failure", recipient, str(result.error or "SMTP error"))

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
            # Check periodically so the web Stop button takes effect during a delay.
            remaining = delay_seconds
            while remaining > 0 and not (should_stop and should_stop()):
                pause = min(remaining, 0.25)
                time.sleep(pause)
                remaining -= pause
