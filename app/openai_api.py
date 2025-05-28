import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def ask_gpt_about_company(scraped_text, emails, row_email):
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
2. Recommend the best email address to contact for a financial inquiry, picking from the found emails or the database email.
3. If no good email is found, say so clearly.

Answer clearly and concisely.
"""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",  # Or your preferred model
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7,
    )
    return response.choices[0].message.content
