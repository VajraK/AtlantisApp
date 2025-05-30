import openai
from config import OPENAI_API_KEY
import logging
from prompts import base_prompt, ventures_prompt, investors_prompt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

openai.api_key = OPENAI_API_KEY

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

        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": prompt_intro},
                {"role": "user", "content": task}
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
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
    lines = []
    for v in ventures[:10]:
        acronym = v.get('Name (Acronym)', '').strip() if v.get('Name (Acronym)') else ''
        industry = v.get('Industry', '').strip() if v.get('Industry') else ''
        notes = v.get('Notes', '').strip() if v.get('Notes') else ''
        raising = v.get('Raising', '').strip() if v.get('Raising') else ''
        lines.append(f"- {acronym} - {industry} - {notes} - {raising}")
    return "\n".join(lines)