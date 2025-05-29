import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import logging
from typing import Tuple, List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

def scrape_website(url: str) -> Tuple[str, List[str]]:
    """Scrape a website's main page and priority paths for content and emails."""
    emails = set()
    text_content = []
    priority_paths = [
        "contact", "contact-us", "about", "about-us",
        "get-in-touch", "support", "help", "connect",
        "reach-us", "contacts"
    ]

    def crawl_page(page_url: str) -> None:
        """Crawl a single page and collect content/emails."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
        }

        try:
            logger.info(f"Attempting to crawl: {page_url}")
            response = requests.get(page_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            page_text = soup.get_text(separator="\n", strip=True)
            text_content.append(page_text)

            found_emails = EMAIL_REGEX.findall(page_text)
            emails.update(found_emails)
            logger.info(f"Found {len(found_emails)} emails on {page_url}")

        except Exception as e:
            logger.warning(f"Failed to crawl {page_url}: {str(e)}")

    try:
        # Always crawl main page first
        logger.info(f"Starting scrape of main page: {url}")
        crawl_page(url)

        # Crawl priority paths
        for path in priority_paths:
            priority_url = urljoin(url, path)
            logger.info(f"Checking priority path: {priority_url}")
            crawl_page(priority_url)

        full_text = "\n".join(text_content)
        logger.info(f"Scraping complete. Total emails found: {len(emails)}")
        return full_text.strip(), sorted(emails)

    except Exception as e:
        error_msg = f"ERROR: {str(e)}"
        logger.error(error_msg)
        return error_msg, []