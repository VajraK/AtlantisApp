import streamlit as st
from config import APP_PASSWORD
import db
import scraper
import openai_api

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

# Prompt for Table ID
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

# Main scraping logic
row = db.get_next_row(table_id)
if row:
    st.write("Next row to process:")
    st.write(row)

    url = row.get("Website")
    if url:
        st.write(f"Scraping URL: {url}")
        scraped_text, emails = scraper.scrape_website(url)

        if isinstance(scraped_text, str) and scraped_text.startswith("ERROR:"):
            st.error(f"Scraping error: {scraped_text}")
        else:
            st.success("Scraping succeeded")

            # Save scraped data in session state for reuse
            st.session_state.scraped_text = scraped_text
            st.session_state.emails = emails

            st.text_area("Scraped Content", scraped_text[:2000])

            if emails:
                st.success("Found Emails:")
                for email in emails:
                    st.write(email)
            else:
                st.info("No emails found.")

            # Button to save scraped content to DB (optional)
            if st.button("Save to DB"):
                db.save_scraped_content(table_id, row["id"], scraped_text)
                st.success("Saved to DB")
                st.rerun()

            # GPT Analysis Button & Display
            if not st.session_state.get("gpt_answer"):
                if st.button("Analyze with GPT"):
                    row_email = row.get("Email", "")
                    gpt_answer = openai_api.ask_gpt_about_company(
                        st.session_state.scraped_text,
                        st.session_state.emails,
                        row_email
                    )
                    st.session_state.gpt_answer = gpt_answer
                    st.rerun()

            if st.session_state.get("gpt_answer"):
                st.subheader("GPT Analysis:")
                st.write(st.session_state.gpt_answer)

                if st.button("Clear GPT analysis"):
                    st.session_state.gpt_answer = None
                    st.rerun()

else:
    st.info("No more unprocessed rows.")
