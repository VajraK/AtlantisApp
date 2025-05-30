import streamlit as st
import time
import os
import logging
import json
import pytz
from datetime import datetime
from pydantic import BaseModel, ValidationError, EmailStr
from typing import List

from config import APP_PASSWORD, OUTREACH_DATABASE_ID, TEST_MODE
import db
import scraper
import openai_api
import email_sender

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
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

# --- Auth ---
if not OUTREACH_DATABASE_ID:
    st.error("Missing Outreach DB ID in environment.")
    logger.critical("Environment variable OUTREACH_DATABASE_ID is not set.")
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Enter password", type="password")
    if password == APP_PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

st.title("Autonomous Web Analyzer")

if TEST_MODE:
    st.markdown(
        "<div style='color: white; background-color: red; padding: 10px; text-align: center; font-weight: bold;'>"
        "⚠️ TEST MODE IS ENABLED ⚠️"
        "</div>",
        unsafe_allow_html=True
    )

# --- Init session state ---
st.session_state.setdefault("selected_mode", None)
st.session_state.setdefault("websites_table", None)
st.session_state.setdefault("info_table", None)
st.session_state.setdefault("delay_minutes", 10)
st.session_state.setdefault("autorun", False)
st.session_state.setdefault("work_start_hour", 9)
st.session_state.setdefault("work_end_hour", 21)
st.session_state.setdefault("work_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])

# --- Setup UI ---
if st.session_state.selected_mode is None:
    st.subheader("Choose Mode and Tables")
    mode = st.radio("Select mode:", ["Ventures", "Investors"])

    try:
        with st.spinner("Loading tables from Outreach DB..."):
            tables = db.get_tables_in_outreach_database()
    except Exception as e:
        logger.exception("Failed to load tables from Outreach DB")
        st.error(f"Failed to load tables: {e}")
        st.stop()

    if not tables:
        st.error("No tables found in Outreach DB.")
        logger.warning("No tables found in Outreach DB.")
        st.stop()

    table_options = {f"{t['name']} (ID: {t['id']})": t['id'] for t in tables}

    websites_table = st.selectbox("Select Websites table", list(table_options.keys()))
    info_table = st.selectbox("Select Info table", list(table_options.keys()))
    delay_minutes = st.number_input("Delay between runs (minutes)", min_value=1, value=10)

    col1, col2 = st.columns(2)
    with col1:
        work_start_hour = st.number_input("Work Start Hour (CET)", min_value=0, max_value=23, value=9)
    with col2:
        work_end_hour = st.number_input("Work End Hour (CET)", min_value=0, max_value=23, value=21)

    work_days = st.multiselect(
        "Select Working Days",
        WEEK_DAYS,
        default=st.session_state.work_days
    )

    if st.button("Confirm Selection"):
        st.session_state.selected_mode = mode
        st.session_state.websites_table = table_options[websites_table]
        st.session_state.info_table = table_options[info_table]
        st.session_state.delay_minutes = delay_minutes
        st.session_state.work_start_hour = work_start_hour
        st.session_state.work_end_hour = work_end_hour
        st.session_state.work_days = work_days
        st.session_state.autorun = True
        st.rerun()

    st.stop()

# --- Helper function to check active hours and days ---

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

# --- Main loop logic ---
def process_next_row():
    try:
        row = db.get_next_row(st.session_state.websites_table)
    except Exception as e:
        logger.exception("Error fetching next row")
        st.error(f"Error fetching next row: {e}")
        return

    if not row:
        st.info("No more unprocessed rows.")
        return

    row_id = row.get("id")
    url = row.get("Website")

    if not url:
        logger.warning(f"Row {row_id}: No website provided.")
        return

    logger.info(f"Row {row_id}: Scraping {url}")
    try:
        scraped_text, emails = scraper.scrape_website(url)
    except Exception as e:
        logger.exception(f"Row {row_id}: Scraping failed for {url}")
        st.error(f"Scraping failed: {e}")
        return

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
            st.error("ERROR: No sufficient text available for analysis.")
            return
    elif word_count > 1000:
        logger.info(f"Row {row_id}: Trimming scraped content from {word_count} to 1000 words.")
        scraped_text = " ".join(scraped_text.split()[:1000])

    try:
        relevant_data = db._get_table_data(st.session_state.info_table)
    except Exception as e:
        logger.exception("Failed to load info table data")
        st.error(f"Error loading info table: {e}")
        return

    logger.info(f"Row {row_id}: Analyzing with GPT...")
    try:
        gpt_result = openai_api.ask_gpt_about_company(
            scraped_text,
            emails,
            row.get("Email", ""),
            st.session_state.selected_mode,
            relevant_data,
            row.get("Location", ""),
            row.get("Total Funding Amount", "")
        )
    except Exception as e:
        logger.exception(f"Row {row_id}: GPT analysis failed.")
        st.error(f"GPT analysis failed: {e}")
        return

    # Validate GPT output with Pydantic
    try:
        # gpt_result expected to be JSON string
        gpt_json = gpt_result if isinstance(gpt_result, dict) else json.loads(gpt_result)
        validated_output = GPTOutput(**gpt_json)
    except (ValidationError, json.JSONDecodeError) as e:
        logger.error(f"Row {row_id}: GPT output validation failed: {e}")
        try:
            db.update_cell(st.session_state.websites_table, row_id, "STATUS", "Skipped")
        except Exception as ex:
            logger.error(f"Row {row_id}: Failed to mark row as Skipped after validation error: {ex}")
        st.error(f"GPT output validation failed: {e}")
        return


    matches = validated_output.matches
    score = max((match.score for match in matches), default=0)
    logger.info(f"Row {row_id}: Highest score from matches: {score}")

    should_send_email = (
        score >= 7 and 
        validated_output.selected_email.strip() and 
        validated_output.subject.strip() and 
        validated_output.email_body.strip()
    )

    if should_send_email:
        logger.info(f"Row {row_id}: Score >=7 and valid email fields present, sending email...")
        try:
            success, msg = email_sender.send_email({
                "selected_email": validated_output.selected_email,
                "subject": validated_output.subject,
                "email_body": validated_output.email_body
            }, row)
        except Exception as e:
            logger.exception(f"Row {row_id}: Email sending raised an exception.")
            st.error(f"Email sending raised exception: {e}")
            return

        if success:
            logger.info(f"Row {row_id}: Email sent, marking as Contacted.")
            try:
                db.update_cell(st.session_state.websites_table, row_id, "STATUS", "Contacted")
            except Exception as e:
                logger.exception(f"Row {row_id}: Failed to update status to Contacted.")
                st.error(f"Failed to update row status: {e}")
        else:
            logger.error(f"Row {row_id}: Email failed to send: {msg}")
            st.error(f"Email sending failed: {msg}")

    else:
        logger.info(f"Row {row_id}: Score below 7 or missing email fields, not sending email.")

    # Mark row as processed regardless
    try:
        db.update_cell(st.session_state.websites_table, row_id, "PROCESSED", True)
        st.success(f"Row {row_id} processed successfully.")
    except Exception as e:
        logger.error(f"Row {row_id}: Failed to mark row as processed: {e}")
        st.error(f"Failed to mark row as processed: {e}")

# --- Autorun Loop ---
if st.session_state.autorun:
    try:
        if is_within_active_hours(st.session_state.work_start_hour, st.session_state.work_end_hour, st.session_state.work_days):
            process_next_row()
            st.write(f"Waiting {st.session_state.delay_minutes} minutes until next run...")
            time.sleep(st.session_state.delay_minutes * 60)
        else:
            st.info(f"Outside active hours or working days, sleeping for 5 minutes.")
            time.sleep(300)
        st.experimental_rerun()
    except Exception as e:
        logger.exception("Unexpected error during autorun loop")
        st.error(f"Unexpected error: {e}")

