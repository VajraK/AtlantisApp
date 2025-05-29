import requests
from config import (
    BASEROW_API_TOKEN, BASEROW_API_URL,
    OUTREACH_DATABASE_ID
)

HEADERS = {"Authorization": f"Token {BASEROW_API_TOKEN}"}

def get_tables_in_outreach_database():
    """Get all tables in the Outreach database (filtered from all-tables)."""
    url = f"{BASEROW_API_URL}/api/database/tables/all-tables/"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    all_tables = response.json()
    outreach_tables = [
        {"id": t["id"], "name": t["name"]}
        for t in all_tables
        if t["database_id"] == int(OUTREACH_DATABASE_ID)
    ]
    return outreach_tables

def _get_table_data(table_id):
    if not table_id:
        return []
    url = f"{BASEROW_API_URL}/api/database/rows/table/{table_id}/?user_field_names=true"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("results", [])

def get_next_row(table_id):
    url = f"{BASEROW_API_URL}/api/database/rows/table/{table_id}/?user_field_names=true"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    rows = response.json().get("results", [])
    for row in rows:
        if row.get("STATUS") != "Contacted":
            return row
    return None

def update_cell(table_id, row_id, field_name, value):
    data = {field_name: value}
    url = f"{BASEROW_API_URL}/api/database/rows/table/{table_id}/{row_id}/?user_field_names=true"
    response = requests.patch(url, headers={**HEADERS, "Content-Type": "application/json"}, json=data)
    response.raise_for_status()
