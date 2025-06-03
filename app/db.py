import requests
import json
from config import (
    BASEROW_API_TOKEN, BASEROW_API_URL,
    OUTREACH_DATABASE_ID
)

HEADERS = {"Authorization": f"Token {BASEROW_API_TOKEN}"}


def get_row(table_id, row_id):
    url = f"{BASEROW_API_URL}api/database/rows/table/{table_id}/{row_id}/?user_field_names=true"

    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch row: {response.status_code} - {response.text}")


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
        status = row.get("STATUS")
        if not status or str(status).strip() in {"", "—"}:
            return row
    return None


def update_cell(table_id, row_id, field_name, value):
    data = {field_name: value}
    url = f"{BASEROW_API_URL}/api/database/rows/table/{table_id}/{row_id}/?user_field_names=true"
    response = requests.patch(url, headers={**HEADERS, "Content-Type": "application/json"}, json=data)
    response.raise_for_status()

def create_main_table_row(
    table_id: int,
    row_data: dict,
    api_url: str = BASEROW_API_URL
) -> dict:
    """
    Creates a new row in the specified Baserow table.

    :param api_token: The Baserow API token
    :param table_id: The ID of the Baserow table
    :param row_data: A dictionary representing the row fields and their values
    :param api_url: The base URL of your Baserow instance
    :return: The JSON response from Baserow
    """
    url = f"{api_url}/api/database/rows/table/{table_id}/?user_field_names=true"

    print("Sending row_data:", json.dumps(row_data, indent=2))  # Pretty-print JSON
    response = requests.post(url, headers=HEADERS, json=row_data)
    response.raise_for_status()  # Will raise an error if the request fails
    return response.json()
