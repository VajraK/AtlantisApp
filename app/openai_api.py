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
    # mandates is a list of dicts with keys like 'Name (Acronym)' and 'Notes'
    lines = []
    for m in mandates[:10]:
        acronym = m.get('Name (Acronym)', '').strip()
        notes = m.get('Notes', '').strip().replace('\n', ' ')
        lines.append(f"- {acronym} - {notes}")
    return "\n".join(lines)

def _format_ventures(ventures):
    # ventures is a list of dicts with keys like 'Name (Acronym)' and 'Industry'
    lines = []
    for v in ventures[:10]:
        acronym = v.get('Name (Acronym)', '').strip()
        industry = v.get('Industry', '').strip()
        notes = v.get('Notes', '').strip()
        raising = v.get('Raising', '').strip()
        lines.append(f"- {acronym} - {industry} - {notes} - {raising}")
    return "\n".join(lines)