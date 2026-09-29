import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

HAS_FLASK = importlib.util.find_spec("flask") is not None
if HAS_FLASK:
    os.environ["WEB_PASSWORD"] = "test-password"
    import webapp


@unittest.skipUnless(HAS_FLASK, "Flask is not installed; install requirements.txt to run web-service tests")
class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.password = webapp.WEB_PASSWORD
        self.log_file = webapp.WEB_LOG_FILE
        self.temp_dir = tempfile.TemporaryDirectory()
        webapp.WEB_PASSWORD = "test-password"
        webapp.WEB_LOG_FILE = Path(self.temp_dir.name) / "web-mailing.log"
        self.app = webapp.create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        webapp.WEB_PASSWORD = self.password
        webapp.WEB_LOG_FILE = self.log_file
        self.temp_dir.cleanup()

    def login(self):
        return self.client.post("/api/login", json={"password": "test-password"})

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/mailing/status").status_code, 401)

    def test_html_pages_redirect_to_login_before_auth(self):
        for path in ("/", "/compose", "/logs", "/settings"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, path)
            self.assertIn("/login?next=", response.headers["Location"])

    def test_login_persists_across_html_navigation(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Expires=", response.headers.get("Set-Cookie", ""))

        for path in ("/", "/compose", "/recipients", "/templates", "/history", "/logs", "/settings"):
            page = self.client.get(path)
            self.assertEqual(page.status_code, 200, path)
            page.close()

        self.assertEqual(self.client.get("/api/settings").status_code, 200)
        self.assertTrue(self.client.get("/api/auth-status").get_json()["authenticated"])

    def test_authenticated_user_does_not_see_login_page(self):
        self.login()
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))

    def test_protected_endpoint_requires_login(self):
        self.assertEqual(self.client.get("/api/settings").status_code, 401)

    def test_start_validates_mailing(self):
        self.login()
        response = self.client.post("/api/mailing/start", json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Добавьте", response.get_json()["error"])

    def test_parse_recipients_removes_duplicates(self):
        self.assertEqual(webapp.parse_recipients("a@example.com, a@example.com\nb@test.ru"), ["a@example.com", "b@test.ru"])

    def test_navigation_pages_are_distinct_documents(self):
        expected_headings = {
            "/compose": "Создайте рассылку",
            "/recipients": "Получатели",
            "/templates": "Шаблоны",
            "/history": "История рассылок",
            "/logs": "СИСТЕМНЫЙ ЖУРНАЛ",
            "/settings": "Настройки",
        }
        self.login()
        for path, heading in expected_headings.items():
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn(heading, response.get_data(as_text=True))
            response.close()

    def test_logs_are_restored_after_service_restart(self):
        service = self.app.config["SERVICE"]
        service._log("Проверка постоянного журнала")
        restarted = webapp.MailingService()
        self.assertEqual(restarted.snapshot()["logs"][-1]["message"], "Проверка постоянного журнала")
