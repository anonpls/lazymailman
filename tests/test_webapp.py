import importlib.util
import os
import unittest

HAS_FLASK = importlib.util.find_spec("flask") is not None
if HAS_FLASK:
    os.environ["WEB_PASSWORD"] = "test-password"
    import webapp


@unittest.skipUnless(HAS_FLASK, "Flask is not installed; install requirements.txt to run web-service tests")
class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.password = webapp.WEB_PASSWORD
        webapp.WEB_PASSWORD = "test-password"
        self.app = webapp.create_app()
        self.client = self.app.test_client()

    def tearDown(self):
        webapp.WEB_PASSWORD = self.password

    def login(self):
        return self.client.post("/api/login", json={"password": "test-password"})

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/mailing/status").status_code, 401)

    def test_login_and_settings(self):
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.client.get("/api/settings").status_code, 200)

    def test_start_validates_mailing(self):
        self.login()
        response = self.client.post("/api/mailing/start", json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Добавьте", response.get_json()["error"])

    def test_parse_recipients_removes_duplicates(self):
        self.assertEqual(webapp.parse_recipients("a@example.com, a@example.com\nb@test.ru"), ["a@example.com", "b@test.ru"])
