import streamlit as st
from config import (
    APP_PASSWORD,
    WEBSITES_VENTURES_TABLE_ID,
    WEBSITES_INVESTORS_TABLE_ID
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

# Mode selection
if "selected_mode" not in st.session_state:
    st.session_state.selected_mode = None
    st.session_state.table_id = None

if st.session_state.selected_mode is None:
    mode = st.radio("Select mode:", ["Ventures", "Investors"])
    if st.button("Confirm Selection"):
        st.session_state.selected_mode = mode
        st.session_state.table_id = (
            WEBSITES_VENTURES_TABLE_ID if mode == "Ventures" 
            else WEBSITES_INVESTORS_TABLE_ID
        )
        logger.info(f"Selected {mode} mode, using table ID: {st.session_state.table_id}")
        st.rerun()
    st.stop()

table_id = st.session_state.table_id

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
                    # Get relevant data based on mode
                    if st.session_state.selected_mode == "Ventures":
                        relevant_data = db.get_all_mandates()
                        logger.info(f"Loaded {len(relevant_data)} mandates")
                    else:
                        relevant_data = db.get_all_ventures()
                        logger.info(f"Loaded {len(relevant_data)} ventures")

                    st.session_state.gpt_answer = openai_api.ask_gpt_about_company(
                        st.session_state.scraped_text,
                        st.session_state.emails,
                        row.get("Email", ""),
                        st.session_state.selected_mode,
                        relevant_data
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