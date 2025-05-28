import requests
from config import BASEROW_API_TOKEN, BASEROW_API_URL

HEADERS = {"Authorization": f"Token {BASEROW_API_TOKEN}"}

def get_next_row(table_id):
    url = f"{BASEROW_API_URL}/api/database/rows/table/{table_id}/?user_field_names=true"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    rows = response.json().get("results", [])
    for row in rows:
        if row.get("STATUS") != "Contacted":
            return row
    return None

def save_scraped_content(table_id, row_id, content):
    data = {
        "Note3": content[:10000],
        "STATUS": "Contacted"
    }
    url = f"{BASEROW_API_URL}/api/database/rows/table/{table_id}/{row_id}/?user_field_names=true"
    response = requests.patch(url, headers={**HEADERS, "Content-Type": "application/json"}, json=data)
    response.raise_for_status()
