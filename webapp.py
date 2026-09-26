"""Flask service for managing Lazy Mailman mailings from the web UI."""
from __future__ import annotations

import os
import secrets
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory, session

import config
from postman import run_mailing
from rewriter import rewrite_email

ROOT = Path(__file__).resolve().parent
WEB_PASSWORD = os.getenv("WEB_PASSWORD")


class MailingService:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.status: dict[str, Any] = self._new_status()

    @staticmethod
    def _new_status() -> dict[str, Any]:
        return {"state": "idle", "total": 0, "sent": 0, "failed": 0, "current": None, "logs": []}

    def _log(self, message: str) -> None:
        with self.lock:
            self.status["logs"].append({"at": datetime.now().strftime("%H:%M:%S"), "message": message})
            self.status["logs"] = self.status["logs"][-100:]

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {**self.status, "logs": list(self.status["logs"])}

    def start(self, data: dict[str, Any]) -> None:
        recipients = parse_recipients(data.get("recipients", ""))
        subject = str(data.get("subject", "")).strip()
        template = str(data.get("template", "")).strip()
        if not recipients:
            raise ValueError("Добавьте хотя бы один email-адрес.")
        if not subject:
            raise ValueError("Укажите тему письма.")
        if not template:
            raise ValueError("Введите текст письма.")
        delay = float(data.get("delay", 0))
        if delay < 0:
            raise ValueError("Задержка не может быть отрицательной.")
        active_from = optional_time(data.get("active_from"), "Время начала")
        active_to = optional_time(data.get("active_to"), "Время окончания")
        sender = str(data.get("sender") or config.EMAIL_SENDER or "").strip()
        if sender not in available_senders():
            raise ValueError("Выберите отправителя, настроенного на сервере.")

        # These files remain the source of truth for CLI runs too.
        (ROOT / config.EMAILS_FILE).write_text("\n".join(recipients) + "\n", encoding="utf-8")
        body_file = ROOT / (config.EMAIL_BODY_FILE or "email.txt")
        body_file.write_text(template + "\n", encoding="utf-8")

        with self.lock:
            if self.status["state"] == "running":
                raise ValueError("Рассылка уже выполняется.")
            self.stop_event.clear()
            self.status = self._new_status()
            self.status.update({"state": "running", "total": len(recipients)})
        self._log(f"Рассылка запущена: получателей {len(recipients)}.")
        self.thread = threading.Thread(
            target=self._run,
            kwargs={"recipients": recipients, "subject": subject, "template": template, "sender": sender,
                    "delay": delay, "active_from": active_from, "active_to": active_to,
                    "rewrite": bool(data.get("rewrite"))},
            daemon=True,
        )
        self.thread.start()

    def _run(self, **args: Any) -> None:
        def event(kind: str, recipient: str, detail: str = "") -> None:
            with self.lock:
                self.status["current"] = recipient if kind == "sending" else None
                if kind == "success": self.status["sent"] += 1
                if kind == "failure": self.status["failed"] += 1
            labels = {"sending": "Отправка", "success": "Отправлено", "failure": "Ошибка"}
            self._log(f"{labels.get(kind, kind)}: {recipient}{': ' + detail if detail else ''}")

        try:
            run_mailing(
                args["recipients"], subject=args["subject"], template=args["template"], sender=args["sender"],
                rewrite_body=rewrite_email if args["rewrite"] else None, delay_seconds=args["delay"],
                primary_password=(config.FALLBACK_GMAIL_APP_PASSWORD if args["sender"] == config.FALLBACK_EMAIL_SENDER else config.GMAIL_APP_PASSWORD),
                active_from=args["active_from"], active_to=args["active_to"],
                should_stop=self.stop_event.is_set, on_event=event,
            )
            with self.lock:
                self.status["state"] = "stopped" if self.stop_event.is_set() else "completed"
                self.status["current"] = None
            self._log("Рассылка остановлена пользователем." if self.stop_event.is_set() else "Рассылка завершена.")
        except Exception as exc:
            with self.lock:
                self.status["state"] = "error"; self.status["current"] = None
            self._log(f"Критическая ошибка: {type(exc).__name__}: {exc}")

    def stop(self) -> bool:
        with self.lock:
            if self.status["state"] != "running": return False
            self.stop_event.set()
        self._log("Запрошена остановка; текущая SMTP-операция будет завершена.")
        return True


def parse_recipients(value: str) -> list[str]:
    items = value.replace(",", "\n").replace(";", "\n").splitlines()
    recipients = [item.strip() for item in items if item.strip()]
    invalid = [item for item in recipients if "@" not in item or "." not in item.rsplit("@", 1)[-1]]
    if invalid: raise ValueError(f"Некорректный email: {invalid[0]}")
    return list(dict.fromkeys(recipients))


def optional_time(value: Any, label: str) -> str | None:
    value = str(value or "").strip()
    if not value: return None
    try: datetime.strptime(value, "%H:%M")
    except ValueError as exc: raise ValueError(f"{label} должно быть в формате ЧЧ:ММ.") from exc
    return value


def available_senders() -> list[str]:
    return [item for item in dict.fromkeys([config.EMAIL_SENDER, config.FALLBACK_EMAIL_SENDER]) if item]


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY") or secrets.token_urlsafe(32)
    app.config["SERVICE"] = MailingService()

    def authorized() -> bool: return session.get("mailman_authenticated", False)
    def protected():
        if not authorized(): return jsonify({"error": "Требуется вход."}), 401
        return None

    @app.get("/")
    def index(): return send_from_directory(ROOT / "web", "index.html")

    @app.get("/<path:filename>")
    def assets(filename: str): return send_from_directory(ROOT / "web", filename)

    @app.post("/api/login")
    def login():
        password = (request.get_json(silent=True) or {}).get("password", "")
        if not WEB_PASSWORD or not secrets.compare_digest(str(password), WEB_PASSWORD):
            return jsonify({"error": "Неверный пароль или WEB_PASSWORD не настроен."}), 401
        session["mailman_authenticated"] = True
        return jsonify({"ok": True})

    @app.post("/api/logout")
    def logout(): session.clear(); return jsonify({"ok": True})

    @app.get("/api/settings")
    def settings():
        denied = protected()
        if denied: return denied
        return jsonify({"senders": available_senders(), "default_sender": config.EMAIL_SENDER,
                        "default_delay": config.EMAIL_SEND_DELAY_SECONDS, "active_from": config.MAILING_ACTIVE_FROM or "",
                        "active_to": config.MAILING_ACTIVE_TO or ""})

    @app.post("/api/mailing/start")
    def start():
        denied = protected()
        if denied: return denied
        try: app.config["SERVICE"].start(request.get_json(force=True))
        except (ValueError, TypeError) as exc: return jsonify({"error": str(exc)}), 400
        return jsonify(app.config["SERVICE"].snapshot()), 202

    @app.post("/api/mailing/stop")
    def stop():
        denied = protected()
        if denied: return denied
        if not app.config["SERVICE"].stop(): return jsonify({"error": "Активной рассылки нет."}), 409
        return jsonify(app.config["SERVICE"].snapshot())

    @app.get("/api/mailing/status")
    def status():
        denied = protected()
        if denied: return denied
        return jsonify(app.config["SERVICE"].snapshot())
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
