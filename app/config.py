import os
from dotenv import load_dotenv
load_dotenv()


BASEROW_API_URL = os.getenv("BASEROW_API_URL", "http://localhost:3000")
BASEROW_API_TOKEN = os.getenv("BASEROW_API_TOKEN", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "letmein")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")