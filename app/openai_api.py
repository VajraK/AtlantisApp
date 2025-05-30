import openai
import logging
import re

from config import OPENAI_API_KEY
from prompts import base_prompt, ventures_prompt, investors_prompt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

openai.api_key = OPENAI_API_KEY

def clean_json_output(json_str: str) -> str:
    """Remove Markdown code block syntax from JSON string if present."""
    json_str = re.sub(r'^\s*```json\s*', '', json_str, flags=re.IGNORECASE)
    json_str = re.sub(r'^\s*```\s*', '', json_str, flags=re.IGNORECASE)
    json_str = re.sub(r'\s*```\s*$', '', json_str, flags=re.IGNORECASE)
    return json_str.strip()

def ask_gpt_about_company(scraped_text: str, emails: list, row_email: str,
                          mode: str, relevant_data: list, location: str, funding: str) -> str:
    try:
        if not scraped_text:
            return "ERROR: No scraped text available for analysis"
        
        prompt_intro = base_prompt(scraped_text, emails, row_email, location, funding)
        
        if mode == "Ventures":
            formatted_mandates = _format_mandates(relevant_data)
            task = ventures_prompt(formatted_mandates)
        else:
            formatted_ventures = _format_ventures(relevant_data)
            task = investors_prompt(formatted_ventures)

        logger.info("Sending request to OpenAI GPT...")

        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": prompt_intro},
                {"role": "user", "content": task}
            ],
            max_tokens=1000,
            temperature=0.7,
        )

        raw_output = response.choices[0].message.content.strip()
        cleaned_output = clean_json_output(raw_output)
        
        logger.info("Received and cleaned response from GPT.")
        return cleaned_output

    except Exception as e:
        logger.error(f"GPT Error: {str(e)}")
        return f"GPT Error: {str(e)}"

def _format_mandates(mandates):
    """Format mandates data with None checks and proper string handling"""
    lines = []
    for m in mandates[:10]:
        acronym = m.get('Name (Acronym)', '').strip() if m.get('Name (Acronym)') else ''
        notes = m.get('Notes', '').strip() if m.get('Notes') else ''
        lines.append(f"- {acronym} - {notes}")
    return "\n".join(lines)

def _format_ventures(ventures):
    """Format ventures data for GPT prompt"""
    lines = []
    for v in ventures[:10]:
        acronym = v.get('Name (Acronym)', '').strip() if v.get('Name (Acronym)') else ''
        industry = v.get('Industry', '').strip() if v.get('Industry') else ''
        notes = v.get('Notes', '').strip() if v.get('Notes') else ''
        raising = v.get('Raising', '').strip() if v.get('Raising') else ''
        lines.append(f"- {acronym} - {industry} - {notes} - {raising}")
    return "\n".join(lines)
