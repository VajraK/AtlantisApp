import time
import os
import logging
import json
import pytz
from datetime import datetime
from pydantic import BaseModel, ValidationError, EmailStr
from typing import List
import random

from config import OUTREACH_DATABASE_ID, TEST_MODE, SENDER_ACCOUNTS, MAIN_VENTURES_TABLE_ID, MAIN_INVESTORS_TABLE_ID
import db
import scraper
import openai_api
import email_sender

# Path to one directory above this script
log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app.log')

# Optional: Remove existing handlers (avoids duplication if re-run in same session)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# --- Pydantic models for GPT output validation ---

class Match(BaseModel):
    acronym: str
    score: int
    fit: bool

class GPTOutput(BaseModel):
    matches: List[Match]
    selected_email: EmailStr
    subject: str
    email_body: str

# --- Constants ---

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# --- Helper functions ---

def get_randomized_delay(base_delay_minutes):
    """Return a random delay within ±20% of the base delay"""
    variation = 0.2  # 20%
    min_delay = base_delay_minutes * (1 - variation)
    max_delay = base_delay_minutes * (1 + variation)
    return random.uniform(min_delay, max_delay)

def prompt_select(prompt, options):
    print(prompt)
    for i, option in enumerate(options, start=1):
        print(f"{i}. {option}")
    while True:
        choice = input(f"Enter number (1-{len(options)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice)-1]
        else:
            print("Invalid choice, please try again.")

def prompt_multiselect(prompt, options, default_selected):
    print(prompt)
    print("Enter numbers separated by commas (e.g. 1,3,5)")
    print("Available options:")
    for i, option in enumerate(options, start=1):
        mark = "(default)" if option in default_selected else ""
        print(f"{i}. {option} {mark}")
    while True:
        user_input = input(f"Selected (default {','.join(default_selected)}): ").strip()
        if user_input == "":
            return default_selected
        selections = user_input.split(",")
        selected = []
        valid = True
        for sel in selections:
            sel = sel.strip()
            if sel.isdigit() and 1 <= int(sel) <= len(options):
                selected.append(options[int(sel)-1])
            else:
                print(f"Invalid selection: {sel}")
                valid = False
                break
        if valid and selected:
            return selected
        else:
            print("Please enter valid numbers separated by commas.")

def choose_sender_account():
    if not SENDER_ACCOUNTS:
        raise ValueError("No sender accounts configured in SENDER_ACCOUNTS.")

    print("Choose a sender account:")
    for i, account in enumerate(SENDER_ACCOUNTS):
        print(f"{i + 1}. {account.get('name')} <{account.get('email')}>")

    while True:
        choice = input(f"Enter number (1-{len(SENDER_ACCOUNTS)}): ")
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(SENDER_ACCOUNTS):
                return SENDER_ACCOUNTS[idx]
        print("Invalid choice. Try again.")


def prompt_int(prompt, min_val, max_val, default):
    while True:
        user_input = input(f"{prompt} [{default}]: ").strip()
        if user_input == "":
            return default
        if user_input.isdigit():
            val = int(user_input)
            if min_val <= val <= max_val:
                return val
        print(f"Invalid input. Enter an integer between {min_val} and {max_val}.")

def is_within_active_hours(start_hour, end_hour, working_days):
    tz = pytz.timezone("Europe/Paris")  # CET timezone with DST awareness
    now = datetime.now(tz)
    current_hour = now.hour
    current_day = now.strftime("%A")  # Full weekday name, e.g. "Monday"

    if current_day not in working_days:
        return False

    if end_hour > start_hour:
        return start_hour <= current_hour < end_hour
    else:
        # Overnight span (e.g. start=22, end=6)
        return current_hour >= start_hour or current_hour < end_hour

def process_next_row(selected_mode, websites_table, info_table, sender_account):
    try:
        row = db.get_next_row(websites_table)
    except Exception as e:
        logger.exception("Error fetching next row")
        print(f"Error fetching next row: {e}")
        return False

    if not row:
        logger.info("No more unprocessed rows.")
        print("No more unprocessed rows.")
        return False

    row_id = row.get("id")
    url = row.get("Website")

    if not url:
        logger.warning(f"Row {row_id}: No website provided.")
        print(f"Row {row_id}: No website provided.")
        return True

    logger.info(f"Row {row_id}: Scraping {url}")
    print(f"Row {row_id}: Scraping {url}")
    try:
        scraped_text, emails = scraper.scrape_website(url)
    except Exception as e:
        logger.exception(f"Row {row_id}: Scraping failed for {url}")
        print(f"Scraping failed: {e}")
        return True

    if not scraped_text or (isinstance(scraped_text, str) and scraped_text.startswith("ERROR")):
        logger.warning(f"Row {row_id}: Scraping failed. Using Description field.")
        scraped_text = row.get("Description", "")

    word_count = len(scraped_text.split())

    if word_count < 10:
        logger.warning(f"Row {row_id}: Scraped content too short ({word_count} words), using Description.")
        scraped_text = row.get("Description", "")
        word_count = len(scraped_text.split())
        if word_count < 10:
            logger.error(f"Row {row_id}: Description also too short ({word_count} words).")
            print("ERROR: No sufficient text available for analysis.")
            return True
    elif word_count > 3000:
        logger.info(f"Row {row_id}: Trimming scraped content from {word_count} to 3000 words.")
        scraped_text = " ".join(scraped_text.split()[:3000])

    try:
        relevant_data = db._get_table_data(info_table)
    except Exception as e:
        logger.exception("Failed to load info table data")
        print(f"Error loading info table: {e}")
        return True

    logger.info(f"Row {row_id}: Analyzing with GPT...")
    print(f"Row {row_id}: Analyzing with GPT...")
    try:
        gpt_result = openai_api.ask_gpt_about_company(
            scraped_text,
            emails,
            row.get("Email", ""),
            selected_mode,
            relevant_data,
            row.get("Location", ""),
            row.get("Total Funding Amount", "")
        )
    except Exception as e:
        logger.exception(f"Row {row_id}: GPT analysis failed.")
        print(f"GPT analysis failed: {e}")
        return True

    # Validate GPT output with Pydantic
    try:
        # gpt_result expected to be JSON string or dict
        gpt_json = gpt_result if isinstance(gpt_result, dict) else json.loads(gpt_result)
        validated_output = GPTOutput(**gpt_json)
    except (ValidationError, json.JSONDecodeError) as e:
        logger.error(f"Row {row_id}: GPT output validation failed: {e}")
        try:
            db.update_cell(websites_table, row_id, "STATUS", "Skipped")
            json_string = json.dumps(gpt_json, ensure_ascii=False)
            db.update_cell(websites_table, row_id, "Note3", json_string)
        except Exception as ex:
            logger.error(f"Row {row_id}: Failed to mark row as Skipped after validation error or Note3: {ex}")
        print(f"GPT output validation failed: {e}")
        return True

    matches = validated_output.matches
    score = max((match.score for match in matches), default=0)
    logger.info(f"Row {row_id}: Highest score from matches: {score}")
    print(f"Row {row_id}: Highest score from matches: {score}")

    should_send_email = (
        score >= 7 and 
        validated_output.selected_email.strip() and 
        validated_output.subject.strip() and 
        validated_output.email_body.strip()
    )

    if should_send_email:
        logger.info(f"Row {row_id}: Score >=7 and valid email fields present, sending email...")
        print(f"Row {row_id}: Score >=7 and valid email fields present, sending email...")
        try:

            success, msg = email_sender.send_email({
                "selected_email": validated_output.selected_email,
                "subject": validated_output.subject,
                "email_body": validated_output.email_body
            }, row, sender_account)
        except Exception as e:
            logger.exception(f"Row {row_id}: Email sending raised an exception.")
            print(f"Email sending raised exception: {e}")
            return True

        if success:
            logger.info(f"Row {row_id}: Email sent, marking as Contacted.")
            print(f"Row {row_id}: Email sent, marking as Contacted.")
            try:
                db.update_cell(websites_table, row_id, "STATUS", "Contacted")
                json_string = json.dumps(gpt_json, ensure_ascii=False)
                db.update_cell(websites_table, row_id, "Note3", json_string)

                # Re-fetch the full row after update
                row = db.get_row(websites_table, row_id)

                if selected_mode == "Ventures":
                    target_table = MAIN_VENTURES_TABLE_ID
                else:  # Investors mode
                    target_table = MAIN_INVESTORS_TABLE_ID
                
                try:
                    # Get the complete row data first
                    keys = ['Name', 'Note3', 'Description', 'Website', 'Email', 'Location', 'Total Funding Amount', 'LinkedIn', 'Phone', 'CB Rank', 'STATUS']
                    complete_row = {key: row.get(key) for key in keys}

                    if selected_mode == "Investors":
                        # Remove 'Total Funding Amount' if present
                        complete_row.pop("Total Funding Amount", None)
                    
                    # Normalize STATUS into a list if it is a string
                    status_value = complete_row.get("STATUS")
                    if status_value:
                        if isinstance(status_value, str):
                            complete_row["STATUS"] = [status_value]
                        elif isinstance(status_value, list):
                            # Already a list, keep as is
                            pass
                        else:
                            # If None or other types, set empty list or handle as needed
                            complete_row["STATUS"] = []

                    else:
                        complete_row["STATUS"] = []
                    
                    if complete_row:
                        # Create the new row in the main table
                        new_row = db.create_main_table_row(
                            table_id=target_table,
                            row_data=complete_row
                        )
                        logger.info(f"Row {row_id}: Successfully created in main {selected_mode} table with ID {new_row.get('id')}")
                        print(f"Row {row_id}: Successfully created in main {selected_mode} table with ID {new_row.get('id')}")
                    else:
                        logger.error(f"Row {row_id}: Could not retrieve complete row data for creating in main table")
                        print("Could not retrieve complete row data for creating in main table")
                except Exception as create_error:
                    logger.error(f"Row {row_id}: Failed to create in main table: {create_error}")
                    print(f"Failed to create in main table: {create_error}")

            except Exception as e:
                logger.exception(f"Row {row_id}: Failed to update status to Contacted or Note3.")
                print(f"Failed to update row status or Note3: {e}")
        else:
            logger.error(f"Row {row_id}: Email failed to send: {msg}")
            print(f"Email sending failed: {msg}")

    else:
        logger.info(f"Row {row_id}: Score below 7 or missing email fields, not sending email.")
        print(f"Row {row_id}: Score below 7 or missing email fields, not sending email.")
        try:
            db.update_cell(websites_table, row_id, "STATUS", "not contacted yet")
            db.update_cell(websites_table, row_id, "Note3", json.dumps(gpt_json))
        except Exception as e:
            logger.exception(f"Row {row_id}: Failed to update STATUS or Note3 for low score.")
            print(f"Failed to update STATUS or Note3: {e}")

    # Mark row as processed regardless
    try:
        db.update_cell(websites_table, row_id, "x", True)
        print(f"Row {row_id} processed successfully.")
    except Exception as e:
        logger.error(f"Row {row_id}: Failed to mark row as processed: {e}")
        print(f"Failed to mark row as processed: {e}")

    return True


def main():
    if not OUTREACH_DATABASE_ID:
        logger.critical("Environment variable OUTREACH_DATABASE_ID is not set.")
        print("Missing Outreach DB ID in environment.")
        exit(1)

    print("=== Autonomous Web Analyzer ===")

    # Load tables
    try:
        tables = db.get_tables_in_outreach_database()
    except Exception as e:
        logger.exception("Failed to load tables from Outreach DB")
        print(f"Failed to load tables: {e}")
        exit(1)

    if not tables:
        logger.warning("No tables found in Outreach DB.")
        print("No tables found in Outreach DB.")
        exit(1)

    table_options = {f"{t['name']} (ID: {t['id']})": t['id'] for t in tables}

    # Select sender account at the beginning
    sender_account = choose_sender_account()
    
    mode = prompt_select("Select mode:", ["Ventures", "Investors"])
    websites_table_key = prompt_select("Select Websites table:", list(table_options.keys()))
    info_table_key = prompt_select("Select Info table:", list(table_options.keys()))

    delay_minutes = prompt_int("Delay between runs (minutes)", 1, 1440, 10)
    work_start_hour = prompt_int("Work Start Hour (CET)", 0, 23, 9)
    work_end_hour = prompt_int("Work End Hour (CET)", 0, 23, 21)
    work_days = prompt_multiselect("Select Working Days", WEEK_DAYS, ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])

    randomized_delay = get_randomized_delay(delay_minutes)

    websites_table = table_options[websites_table_key]
    info_table = table_options[info_table_key]

    if TEST_MODE:
        print("⚠️ TEST MODE IS ENABLED ⚠️")

    print(f"Configuration:")
    print(f"Mode: {mode}")
    print(f"Websites Table: {websites_table_key}")
    print(f"Info Table: {info_table_key}")
    print(f"Sender Account: {sender_account['name']} <{sender_account['email']}>")
    print(f"Delay between runs: {delay_minutes} minutes")
    print(f"Working hours: {work_start_hour}:00 to {work_end_hour}:00 CET")
    print(f"Working days: {', '.join(work_days)}")
    print("Starting processing loop...")

    try:
        while True:
            if is_within_active_hours(work_start_hour, work_end_hour, work_days):
                has_more = process_next_row(mode, websites_table, info_table, sender_account)
                if not has_more:
                    print(f"No more rows to process. Sleeping for {randomized_delay:.1f} minutes...")
                    time.sleep(randomized_delay * 60)
                else:
                    print(f"Waiting {randomized_delay:.1f} minutes until next processing cycle...")
                    time.sleep(randomized_delay * 60)
            else:
                print("Outside working hours. Sleeping for 5 minutes...")
                time.sleep(5 * 60)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
    except Exception as e:
        logger.exception("Fatal error in main loop")
        print(f"Fatal error: {e}")


if __name__ == "__main__":
    main()
