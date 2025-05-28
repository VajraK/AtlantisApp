import openai
from config import OPENAI_API_KEY
import logging
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

openai.api_key = OPENAI_API_KEY

def ask_gpt_about_company(scraped_text: str, emails: list, row_email: str) -> str:
    """Analyze company information using GPT with enhanced error handling."""
    try:
        if not OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        if not scraped_text or len(scraped_text) < 50:
            raise ValueError("Insufficient scraped text for analysis")

        prompt = f"""
You are an expert financial assistant.

Here is some scraped text about a company:

\"\"\"{scraped_text[:3000]}\"\"\"

Here are some emails found on the website:
{', '.join(emails) if emails else 'None'}

The email address from the database row is:
{row_email}

Please:
1. Summarize what you know about the company from the scraped text.
2. Recommend the best email address to contact for a financial inquiry, picking from the found emails or the database email (If no good email is found, say so clearly).

Answer clearly and concisely.
"""
        logger.info("Sending request to OpenAI API...")
        
        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a helpful financial analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7,
        )
        
        result = response.choices[0].message.content.strip()
        logger.info("Successfully received GPT response")
        return result
    
    except Exception as e:
        error_msg = f"GPT Analysis Error: {str(e)}"
        logger.error(error_msg)
        return error_msg