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

def ask_gpt_about_company(scraped_text: str, emails: list, row_email: str, 
                         mode: str, relevant_data: list) -> str:
    """Analyze company and generate appropriate email based on mode"""
    try:
        if not scraped_text:
            return "ERROR: No scraped text available for analysis"
            
        base_prompt = f"""
You are an expert matchmaking assistant for an advisory firm. Analyze this company:

Scraped text:
\"\"\"{scraped_text[:3000]}\"\"\"

Found emails: {', '.join(emails) if emails else 'None'}
Database email: {row_email if row_email else 'None'}
"""
        if mode == "Ventures":
            analysis_task = f"""
REQUIRED ANALYSIS:
1. Identify which mandates are top 1-2 matches this company's profile (format: [Acronym - Notes]):
{_format_mandates(relevant_data)}
 
2. Draft email to company contact proposing these matches (without mentioning their acronyms)

EMAIL GUIDELINES:
- Start with brief introduction (say that my name is Vajra Kantor and I am a reasearcher with Atlantis Pathways, an advisiory firm that is now connecting ventures with investors)
- Reference specific mandates that match their business, mention that we are partnered with these investors
- Keep under 300 words
- Professional but enthusiastic tone
- Say Dear [Venture-name] Team and sign as Vajra Kantor, Atlantis Pathways
"""
        else:  # Investors
            analysis_task = f"""
REQUIRED ANALYSIS:
1. Review these ventures (format: [Acronym - Industry - Notes - Raising]):
{_format_ventures(relevant_data)}

2. Identify which ventures match this investor's focus areas
3. For top 1-2 matches, explain why they're relevant  
4. Draft email to investor proposing ventures

EMAIL GUIDELINES:  
- Start with brief introduction (say that my name is Vajra Kantor and I am a reasearcher with Atlantis Pathways, an advisiory firm that is now connecting ventures with investors)
- Reference specific ventures matching their interests
- Keep under 300 words
- Professional but enthusiastic tone
- Include placeholders for [CONTACT NAME] and sign as Vajra Kantor, Atlantis Pathways
"""

        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": base_prompt},
                {"role": "user", "content": analysis_task}
            ],
            max_tokens=600,
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