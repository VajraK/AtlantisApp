def base_prompt(scraped_text: str, emails: list, row_email: str, location: str, funding: str) -> str:
    return f"""
You are an expert matchmaking assistant for an advisory firm analyzing companies and investor mandates.

Here is the data about a company:

Scraped Text (may be truncated):
\"\"\"{scraped_text[:3000]}\"\"\"

Found emails: {', '.join(emails) if emails else 'None'}
Database email: {row_email if row_email else 'None'}
"""

def ventures_prompt(mandates: str) -> str:
    return f"""
You are a professional investment analyst assistant helping match ventures to investor mandates.

{chr(10).join(f"- {m}" for m in mandates)}

Your task has three parts:

1. For each mandate, score how well the company fits on a scale of 1–10:
   - 10 = Perfect match
   - 7-9 = Strong match
   - 1-6 = Weak or no match
   Only those with a score **7 or higher** are considered a "fit".

   When scoring, consider factors such as:
   - Industry alignment
   - Stage of company
   - Fundraising amount
   - Geography (if relevant)
   - Any specific mandate notes

   Mandates to evaluate (format: [Acronym - Notes]):
   {mandates}

2. From the list of found and database emails, choose the single most appropriate address for contacting this company about **fundraising**.
   - If it is a **generic** address (e.g., info@, contact@), greeting should be: **"Dear [Company Name] Team,"**
   - If it is a **personal** address (e.g., john.smith@company.com) and you know the full name, greeting may be: **"Dear [Full Name],"**
   - If uncertain, default to: **"Dear [Company Name] Team,"**

3. If there is at least one strong fit (score ≥ 7):
   - Select the one category with the **highest** score.
   - Write a concise, professional, kind email (under 300 words, ideally under 200) from **Vajra Kantor at Hope Capital Advisors**.
   - Subject line should read: **"Exploring Funding Opportunities for [Company Name]"**.
   - In the body:
     - Mention that you recently reviewed their website and were impressed by a key aspect of their work (based on the scraped data).
     - Reference the relevant category (called "mandate") that is the best fit.
     - Note that you have a strong network of capital partners focused on that sector.
     - Invite them to a brief conversation about their growth plans and potential alignment.

Output the result as a valid JSON object with the following structure:

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
You are a professional investment analyst assistant helping match investors to appropriate venture opportunities.

Your task has three parts:

1. For each of the following ventures, score how well it matches the investor’s focus on a scale of 1–10, where:
   - 10 = Perfect match
   - 7-9 = Strong match
   - 1-6 = Weak or no match

Only consider those with a score **7 or higher** as a "fit".

When scoring, consider:
- Industry alignment
- Company stage
- Fundraising size
- Geographic focus
- Specific investor notes

Ventures to evaluate (format: [Acronym - Industry - Notes - Raising]):
{ventures}

2. From the list of found and database emails, choose the one most appropriate for contacting this investor about **Investment Opportunities**.

- If the selected email is a **generic address** (e.g. info@, contact@), write the email greeting as: **"Dear [Investor Firm Name] Team,"**
- If the email is **clearly personal** (e.g. john.smith@...) **and** the contact name is confidently known, use: **"Dear [Full Name],"**
- **If uncertain, default to**: **"Dear [Investor Firm Name] Team,"**

3. Write a short professional email proposing a connection, **only if there are strong matches (score ≥ 7)**.
- Say your name is Vajra Kantor, researcher at Atlantis Pathways, an advisory firm helping its partnered investors in finding new ventures to support.
- Mention that you are reaching out to potentially connect them with your client ventures.
- Reference the **relevant matched mandates** (score ≥ 7) — do **not** mention acronyms.
- Mention they can find out a bit more about your current ventures at **atlantispathways.com**.
- Use a tone that is professional, but kind.
- Keep the email ideally under **200 words**, and **never more than 300 words**.

Output the result as a valid JSON object in this format:

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

If there are no fits with score ≥ 7, output the same JSON structure, but with:
"selected_email": "",
"subject": "",
"email_body": ""
"""
