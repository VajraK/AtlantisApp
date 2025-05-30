def base_prompt(scraped_text: str, emails: list, row_email: str, location: str, funding: str) -> str:
    return f"""
You are an expert matchmaking assistant for an advisory firm analyzing companies and investor mandates.

Here is the data about a company:
Location: {location or 'Unknown'}
Total Funding Amount: {funding or 'Unknown'}

Scraped Text:
\"\"\"{scraped_text[:3000]}\"\"\"

Found emails: {', '.join(emails) if emails else 'None'}
Database email: {row_email if row_email else 'None'}
"""

def ventures_prompt(mandates: str) -> str:
    return f"""
Your task has three parts:

1. For each of the following mandates, score how well it matches the company on a scale of 1–10, where:
   - 10 = Perfect match
   - 7-9 = Strong match
   - 1-6 = Weak or no match

Only consider those with a score **7 or higher** as a "fit".

Mandates to evaluate (format: [Acronym - Notes]):
{mandates}

2. From the list of found and database emails, choose the one most appropriate for contacting this company about **Fund Raising**.

3. Write a short professional email proposing a connection, **only if there are strong matches (score ≥ 7)**.
- Start with: "Dear [Venture-name] Team,"
- Say your name is Vajra Kantor, researcher at Atlantis Pathways, an advisory firm connecting ventures with investors, and that we would be interested to potentially connecting them with investors in our network.
- Reference relevant matched mandates (score ≥ 7) ((do not mention acronyms)).
- Say that they can find out more about our current investor mandates on our website (atlantispathways.com).
- Keep under 300 words.
- Professional and enthusiastic.

Finally, output the entire result as a valid JSON object with the following structure:

{{
  "matches": [
    {{
      "acronym": "Mandate1",
      "score": 9,
      "fit": true
    }},
    {{
      "acronym": "Mandate2",
      "score": 6,
      "fit": false
    }}
  ],
  "selected_email": "someone@example.com",
  "subject": "Your email subject here",
  "email_body": "Your full email message here"
}}

If there are no fits with score ≥ 7, output the same JSON structure, but with:
"selected_email": "",
"subject": "",
"email_body": ""
"""

def investors_prompt(ventures: str) -> str:
    return f"""
Your task has three parts:

1. For each of the following ventures, score how well it matches this investor’s focus on a scale of 1–10, where:
   - 10 = Perfect match
   - 7-9 = Strong match
   - 1-6 = Weak or no match

Only consider those with a score **7 or higher** as a "fit".

Ventures to evaluate (format: [Acronym - Industry - Notes - Raising]):
{ventures}

2. From the list of found and database emails, choose the one most appropriate for contacting this investor about **Investment Opportunities**.

3. Write a short professional email proposing a connection, **only if there are strong matches (score ≥ 7)**.
- Start with: "Dear [CONTACT NAME],"
- Say your name is Vajra Kantor, researcher at Atlantis Pathways, an advisory firm connecting ventures with investors, and that we would be interested in exploring potential partnership between us and them.
- Reference relevant matched ventures (score ≥ 7) ((do not mention acronyms)).
- Say that they can find out more about our current partnered ventures on our website (atlantispathways.com).
- Keep under 300 words.
- Professional and enthusiastic.

{{
  "matches": [
    {{
      "acronym": "Venture1",
      "score": 9,
      "fit": true
    }},
    {{
      "acronym": "Venture2",
      "score": 5,
      "fit": false
    }}
  ],
  "selected_email": "someone@example.com",
  "subject": "Your email subject here",
  "email_body": "Your full email message here"
}}

If there are no fits with score ≥ 7, the "matches" list should still include all ventures with their scores, but the email fields must be:

If there are no fits with score ≥ 7, output the same JSON structure, but with:
"selected_email": "",
"subject": "",
"email_body": ""
"""
