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

        if not scraped_text:
            logger.error(f"Row {row_id}: No text available for analysis.")
            st.error("ERROR: No scraped text or description available for analysis.")
            return

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

    try:
        logger.info(f"Row {row_id}: Saving GPT result to Note3")
        db.update_cell(st.session_state.websites_table, row_id, "Note3", str(gpt_result))
    except Exception as e:
        logger.exception(f"Row {row_id}: Failed to save GPT result.")
        st.error(f"Failed to save GPT result: {e}")
        return

    # Parse GPT JSON
    try:
        gpt_data = json.loads(gpt_result) if isinstance(gpt_result, str) else gpt_result
    except Exception as e:
        logger.error(f"Row {row_id}: Failed to parse GPT JSON: {e}")
        st.error(f"Failed to parse GPT result JSON: {e}")
        return

    matches = gpt_data.get("matches", [])
    score = max((match.get("score", 0) for match in matches), default=0)
    logger.info(f"Row {row_id}: Highest score from matches: {score}")

    # Check if we should send email (score >=7 AND all email fields are present and non-empty)
    should_send_email = (
        score >= 7 and 
        gpt_data.get("selected_email", "").strip() and 
        gpt_data.get("subject", "").strip() and 
        gpt_data.get("email_body", "").strip()
    )

    if should_send_email:
        logger.info(f"Row {row_id}: Score >=7 and valid email fields present, sending email...")
        try:
            success, msg = email_sender.send_email(gpt_data, row)
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
            st.error(f"Email send failed: {msg}")
    else:
        status_reason = (
            "score <7" if score <7 
            else "missing or empty email fields (selected_email, subject, or email_body)"
        )
        logger.info(f"Row {row_id}: Not sending email ({status_reason}). Marking as not contacted yet.")
        try:
            db.update_cell(st.session_state.websites_table, row_id, "STATUS", "not contacted yet")
        except Exception as e:
            logger.exception(f"Row {row_id}: Failed to update status to not contacted yet.")
            st.error(f"Failed to update row status: {e}")

    st.success(f"Row {row_id} processed successfully!")

# --- Autorun Loop ---
if st.session_state.autorun:
    try:
        process_next_row()
        st.write(f"Waiting {st.session_state.delay_minutes} minutes until next run...")
        time.sleep(st.session_state.delay_minutes * 60)
        st.rerun()
    except Exception as e:
        logger.exception("Unexpected error during autorun")
        st.error(f"Unexpected error: {e}")
else:
    st.info("Autorun is off. Enable it from setup.")