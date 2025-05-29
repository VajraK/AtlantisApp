import streamlit as st
import time
import os
import logging
import json
from config import APP_PASSWORD, OUTREACH_DATABASE_ID, TEST_MODE
import db
import scraper
import openai_api
import email_sender

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Auth ---
if not OUTREACH_DATABASE_ID:
    st.error("Missing Outreach DB ID in environment.")
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
if "selected_mode" not in st.session_state:
    st.session_state.selected_mode = None
if "websites_table" not in st.session_state:
    st.session_state.websites_table = None
if "info_table" not in st.session_state:
    st.session_state.info_table = None
if "delay_minutes" not in st.session_state:
    st.session_state.delay_minutes = 10
if "autorun" not in st.session_state:
    st.session_state.autorun = False

# --- Setup UI ---
if st.session_state.selected_mode is None:
    st.subheader("Choose Mode and Tables")
    mode = st.radio("Select mode:", ["Ventures", "Investors"])

    with st.spinner("Loading tables from Outreach DB..."):
        tables = db.get_tables_in_outreach_database()

    if not tables:
        st.error("No tables found in Outreach DB.")
        st.stop()

    table_options = {f"{t['name']} (ID: {t['id']})": t['id'] for t in tables}

    websites_table = st.selectbox("Select Websites table", list(table_options.keys()))
    info_table = st.selectbox("Select Info table", list(table_options.keys()))
    delay_minutes = st.number_input("Delay between runs (minutes)", min_value=1, value=10)
    autorun = st.checkbox("Auto-run scraping + analysis + email loop")

    if st.button("Confirm Selection"):
        st.session_state.selected_mode = mode
        st.session_state.websites_table = table_options[websites_table]
        st.session_state.info_table = table_options[info_table]
        st.session_state.delay_minutes = delay_minutes
        st.session_state.autorun = autorun
        st.rerun()

    st.stop()

# --- Main loop logic ---
def process_next_row():
    row = db.get_next_row(st.session_state.websites_table)
    if not row:
        st.info("No more unprocessed rows.")
        return

    row_id = row.get("id")
    url = row.get("Website")

    if not url:
        logger.warning("No website found for row.")
        return

    logger.info(f"Scraping: {url}")
    scraped_text, emails = scraper.scrape_website(url)

    if isinstance(scraped_text, str) and scraped_text.startswith("ERROR"):
        logger.error(f"Scraping failed for row {row_id}")
        return

    relevant_data = db._get_table_data(st.session_state.info_table)

    logger.info("Analyzing with GPT...")
    gpt_result = openai_api.ask_gpt_about_company(
        scraped_text,
        emails,
        row.get("Email", ""),
        st.session_state.selected_mode,
        relevant_data,
        row.get("Location", ""),
        row.get("Total Funding Amount", "")
    )

    logger.info("Saving GPT result to Note3")
    db.update_cell(st.session_state.websites_table, row_id, "Note3", str(gpt_result))

    # Parse GPT result to check score before sending email
    try:
        if isinstance(gpt_result, str):
            gpt_data = json.loads(gpt_result)
        else:
            gpt_data = gpt_result
    except Exception as e:
        logger.error(f"Failed to parse GPT result JSON: {e}")
        st.error(f"Failed to parse GPT result JSON: {e}")
        return

    # Extract highest score from matches list
    matches = gpt_data.get("matches", [])
    if matches:
        score = max(match.get("score", 0) for match in matches)
    else:
        score = 0

    logger.info(f"Highest score from matches: {score}")

    if score >= 7:
        logger.info("Score >= 7, sending email...")
        success, msg = email_sender.send_email(gpt_result, row)
        if success:
            logger.info("Email sent, marking as Contacted")
            db.update_cell(st.session_state.websites_table, row_id, "STATUS", "Contacted")
        else:
            logger.error(f"Email send failed: {msg}")
            st.error(f"Email send failed: {msg}")
            # Optionally do not update STATUS here or set to error state
    else:
        logger.info("Score < 7, not sending email, marking as Not Contacted Yet")
        db.update_cell(st.session_state.websites_table, row_id, "STATUS", "not contacted yet")

    st.success(f"Row {row_id} processed successfully!")

# --- Autorun Loop ---
if st.session_state.autorun:
    process_next_row()
    st.write(f"Waiting {st.session_state.delay_minutes} minutes until next run...")
    time.sleep(st.session_state.delay_minutes * 60)
    st.rerun()
else:
    st.info("Autorun is off. Enable it from setup.")
