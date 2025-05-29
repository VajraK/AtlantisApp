import streamlit as st
from config import (
    APP_PASSWORD,
    OUTREACH_DATABASE_ID
)
import db
import scraper
import openai_api
import logging
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

# Ensure Outreach DB is available
if not OUTREACH_DATABASE_ID:
    st.error("Missing Outreach DB ID in environment.")
    st.stop()

# Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Enter password", type="password")
    if password == APP_PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

st.title("Web Analyzer")

# Initial session state
if "selected_mode" not in st.session_state:
    st.session_state.selected_mode = None
if "websites_table" not in st.session_state:
    st.session_state.websites_table = None
if "info_table" not in st.session_state:
    st.session_state.info_table = None

# Mode + Table selection
if st.session_state.selected_mode is None or not st.session_state.websites_table or not st.session_state.info_table:
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

    if st.button("Confirm Selection"):
        st.session_state.selected_mode = mode
        st.session_state.websites_table = table_options[websites_table]
        st.session_state.info_table = table_options[info_table]
        st.rerun()

    st.stop()

# Use selected tables from session
table_id = st.session_state.websites_table
info_table_id = st.session_state.info_table
mode = st.session_state.selected_mode

# Main processing
row = db.get_next_row(table_id)
if row:
    logger.info(f"Processing row: {row.get('id')}")
    st.write("Next row to process:")
    st.write(row)

    url = row.get("Website")
    if url:
        current_row_id = row["id"]

        # Check if we need fresh data
        if ("current_row_id" not in st.session_state or 
            st.session_state.current_row_id != current_row_id):

            logger.info(f"Starting new scrape for URL: {url}")
            scraped_text, emails = scraper.scrape_website(url)

            if isinstance(scraped_text, str) and scraped_text.startswith("ERROR:"):
                logger.error(f"Scraping failed: {scraped_text}")
                st.error(f"Scraping error: {scraped_text}")
                st.stop()
            else:
                logger.info("Scraping completed successfully")
                st.session_state.scraped_text = scraped_text
                st.session_state.emails = emails
                st.session_state.current_row_id = current_row_id
                st.session_state.gpt_answer = None
                st.session_state.gpt_analysis_requested = False
        else:
            logger.info("Using cached scraped data")
            scraped_text = st.session_state.scraped_text
            emails = st.session_state.emails

        # Display scraped content
        st.text_area("Scraped Content", scraped_text[:2000], height=300)

        if emails:
            st.success(f"Found {len(emails)} emails:")
            for email in emails:
                st.write(email)
        else:
            st.info("No emails found.")

        # Save to DB button
        if st.button("Save to DB"):
            logger.info("Saving data to database...")
            db.save_scraped_content(table_id, row["id"], scraped_text)
            st.success("Saved to DB")
            st.rerun()

        # GPT Analysis Section
        if st.button("Analyze with GPT"):
            logger.info("Starting GPT analysis...")
            with st.spinner("Analyzing with GPT..."):
                try:
                    relevant_data = db._get_table_data(info_table_id)
                    logger.info(f"Loaded {len(relevant_data)} entries from info table")

                    st.session_state.gpt_answer = openai_api.ask_gpt_about_company(
                        st.session_state.scraped_text,
                        st.session_state.emails,
                        row.get("Email", ""),
                        mode,
                        relevant_data,
                        row.get("Location", ""),       # add Location from the row here
                        row.get("Total Funding Amount", "")  # add Funding amount here
                    )
                    logger.info("GPT analysis completed")
                except Exception as e:
                    st.session_state.gpt_answer = f"Analysis failed: {str(e)}"
                    logger.error(f"GPT analysis failed: {str(e)}")
            st.rerun()

        if st.session_state.get("gpt_answer"):
            st.subheader("GPT Analysis:")
            st.write(st.session_state.gpt_answer)

            # Add email sending section with more details
            if st.button("Send Email"):
                with st.spinner("Sending email..."):
                    success, message = email_sender.send_email(
                        subject=f"Potential Match from Atlantis Pathways",
                        body=st.session_state.gpt_answer
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(f"Failed to send email: {message}")
                        st.info("Please check your SMTP configuration in .env file")

            if st.button("Clear Analysis"):
                st.session_state.gpt_answer = None
                st.rerun()

else:
    logger.info("No more unprocessed rows")
    st.info("No more unprocessed rows.")
