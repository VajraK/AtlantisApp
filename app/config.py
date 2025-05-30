import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

APP_PASSWORD = config.get("APP_PASSWORD", "letmein")
OPENAI_API_KEY = config.get("OPENAI_API_KEY")
OUTREACH_DATABASE_ID = config.get("OUTREACH_DATABASE_ID")
MAIN_VENTURES_TABLE_ID = config.get("MAIN_VENTURES_TABLE_ID")
MAIN_INVESTORS_TABLE_ID = config.get("MAIN_INVESTORS_TABLE_ID")

BASEROW_API_URL = config.get("BASEROW_API_URL"")
BASEROW_API_TOKEN = config.get("BASEROW_API_TOKEN", "")

# Load sender accounts list
SENDER_ACCOUNTS = config.get("SENDER_ACCOUNTS", [])

TEST_EMAIL_ADDRESS = config.get("TEST_EMAIL_ADDRESS")
TEST_MODE = bool(config.get("TEST_MODE", True))
