import streamlit as st
from config import APP_PASSWORD
import db
import scraper
import openai_api
import logging

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

# Table ID input
if "table_id" not in st.session_state:
    st.session_state.table_id = None

if st.session_state.table_id is None:
    input_id = st.text_input("Enter Table ID")
    if input_id.isdigit():
        st.session_state.table_id = int(input_id)
        st.rerun()
    else:
        st.warning("Please enter a valid numeric Table ID.")
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
                    st.session_state.gpt_answer = openai_api.ask_gpt_about_company(
                        st.session_state.scraped_text,
                        st.session_state.emails,
                        row.get("Email", "")
                    )
                    logger.info("GPT analysis completed")
                except Exception as e:
                    st.session_state.gpt_answer = f"Analysis failed: {str(e)}"
                    logger.error(f"GPT analysis failed: {str(e)}")
            st.rerun()

        if st.session_state.get("gpt_answer"):
            st.subheader("GPT Analysis:")
            st.write(st.session_state.gpt_answer)

            if st.button("Clear Analysis"):
                st.session_state.gpt_answer = None
                st.rerun()

else:
    logger.info("No more unprocessed rows")
    st.info("No more unprocessed rows.")