import os
import dotenv


dotenv.load_dotenv(Override = True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")