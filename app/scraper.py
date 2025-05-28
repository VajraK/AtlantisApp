import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

def scrape_website(url, max_internal_pages=10):
    visited = set()
    emails = set()
    text_content = []

    base_domain = urlparse(url).netloc
    base_url = f"{urlparse(url).scheme}://{base_domain}"
    priority_paths = [
    "/contact/", "/contact-us/", "/about/", "/about-us/",
    "/get-in-touch/", "/support/", "/help/", "/connect/",
    "/reach-us/", "/contacts/", "/en/contact/"]

    internal_links_to_crawl = []

    def log(msg):
        print(msg)
        if "logger" in globals():
            logger(msg)

    def is_internal_http_link(href):
        if href.startswith("mailto:") or href.startswith("tel:"):
            return False
        parsed = urlparse(href)
        return not parsed.netloc or parsed.netloc == base_domain

    def crawl(current_url):
        if current_url in visited:
            return
        visited.add(current_url)

        try:
            log(f"Crawling: {current_url}")
            response = requests.get(current_url, timeout=10)
            response.raise_for_status()
        except Exception as e:
            log(f"Failed to fetch {current_url}: {e}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        page_text = soup.get_text(separator="\n")
        text_content.append(page_text)

        found_emails = EMAIL_REGEX.findall(page_text)
        emails.update(found_emails)

        # Collect internal links only from the main page crawl
        if current_url == url:
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(current_url, href)
                if is_internal_http_link(href) and full_url not in visited:
                    internal_links_to_crawl.append(full_url)

    # Attach logger if inside Streamlit
    global logger
    logger = lambda msg: None
    try:
        import streamlit as st
        logger = st.write
    except ImportError:
        pass

    try:
        log(f"Starting scrape from: {url}")

        # Step 1: Crawl main page
        crawl(url)

        # Step 2: Crawl up to max_internal_pages internal links
        for link in internal_links_to_crawl:
            if len(visited) >= max_internal_pages + 1:  # +1 because main page already visited
                break
            crawl(link)

        # Step 3: Always crawl priority paths
        for path in priority_paths:
            full_url = urljoin(base_url, path)
            crawl(full_url)

        full_text = "\n".join(text_content)
        log(f"Scraping complete. Pages visited: {len(visited)}. Emails found: {len(emails)}")
        return full_text.strip(), sorted(emails)

    except Exception as e:
        log(f"ERROR: {e}")
        return f"ERROR: {e}", []
