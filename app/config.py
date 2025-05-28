import os
from dotenv import load_dotenv
load_dotenv()

# Authentication
APP_PASSWORD = os.getenv("APP_PASSWORD", "letmein")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Table IDs
VENTURES_TABLE_ID = os.getenv("VENTURES_TABLE_ID")
MANDATES_TABLE_ID = os.getenv("MANDATES_TABLE_ID")
WEBSITES_VENTURES_TABLE_ID = os.getenv("WEBSITES_VENTURES_TABLE_ID")
WEBSITES_INVESTORS_TABLE_ID = os.getenv("WEBSITES_INVESTORS_TABLE_ID")

# Baserow config
BASEROW_API_URL = os.getenv("BASEROW_API_URL", "http://localhost:3000")
BASEROW_API_TOKEN = os.getenv("BASEROW_API_TOKEN", "")

# Email
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
TEST_EMAIL_ADDRESS = os.getenv("TEST_EMAIL_ADDRESS")