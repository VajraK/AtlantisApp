# AtlantisApp - Autonomous Outreach Platform

![Atlantis Logo](https://atlantispathways.com/wp-content/uploads/2025/01/LOGO.png)

An AI-powered platform that analyzes companies/investors, matches them to relevant opportunities, and automates outreach emails using GPT-4.

## Features

- 🕸️ Website scraping with priority path crawling
- 🤖 GPT-4 analysis of scraped content
- 📧 Automated email generation and sending
- 🔍 Match scoring system (1-10) for opportunities
- ⏱️ Time-aware scheduling (CET business hours)
- 📊 Baserow database integration
- 🐳 Docker support for local Baserow instance

## Prerequisites

- Python 3.9+
- OpenAI API key
- Baserow account (self-hosted or cloud)
- SMTP email credentials
- Docker (for local Baserow)

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/AtlantisApp.git
cd AtlantisApp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Rename config files:
   ```bash
   cp config_example.json config.json
   cp docker-compose_example.yml docker-compose.yml
   ```
2. Edit `config.json` with your credentials:
   ```json
   {
     "APP_PASSWORD": "your_secure_password",
     "OPENAI_API_KEY": "sk-your-openai-key",
     "OUTREACH_DATABASE_ID": "your_baserow_db_id",
     "MAIN_VENTURES_TABLE_ID": "table_id_1",
     "MAIN_INVESTORS_TABLE_ID": "table_id_2",
     "BASEROW_API_URL": "https://api.baserow.io",
     "BASEROW_API_TOKEN": "your_baserow_token",
     "SENDER_ACCOUNTS": [
       {
         "name": "Your Name",
         "email": "you@domain.com",
         "smtp_server": "smtp.domain.com",
         "smtp_port": 587,
         "smtp_username": "you@domain.com",
         "smtp_password": "your_email_password"
       }
     ],
     "TEST_EMAIL_ADDRESS": "test@domain.com",
     "TEST_MODE": true
   }
   ```

## Database Setup

1. Start local Baserow (optional):
   ```bash
   docker-compose up -d
   ```
2. Create two Baserow database with:
   - Websites table (columns: Name, Website, Email, etc.)
   - Ventures/Mandates info tables
   - Main Databses
     (for details, ask Vajra Kantor — vajra@atlantispathways.com)

## Usage

```bash
python app/app.py
```

The interactive CLI will guide you through:

1. Mode selection (Ventures/Investors)
2. Table selection
3. Sender account choice
4. Scheduling parameters

## Workflow

1. Scrapes company/investor websites
2. Analyzes content with GPT-4
3. Scores matches (1-10)
4. Generates personalized emails for matches ≥7
5. Sends emails via SMTP
6. Updates database status
7. Copies qualified matches to main tables

## File Structure

```
AtlantisApp
├── app
│   ├── app.py              # Main application logic
│   ├── config.py           # Configuration loader
│   ├── db.py               # Baserow database operations
│   ├── email_sender.py     # SMTP email handling
│   ├── openai_api.py       # GPT-4 integration
│   ├── prompts.py          # AI prompt templates
│   └── scraper.py          # Website scraping utility
├── config.json             # Configuration file (ignored in Git)
├── docker-compose.yml      # Baserow Docker configuration
└── requirements.txt        # Python dependencies
```

## Customization

Modify prompts in `prompts.py` for:

- Different email templates
- Matching criteria adjustments
- Industry-specific parameters

## Troubleshooting

Common issues:

- **Scraping failures**: Ensure target websites allow scraping
- **SMTP errors**: Verify port (465/587) and enable "Less Secure Apps"
- **GPT validation errors**: Check prompt outputs match JSON schema
- **Baserow connection issues**: Validate API token and table permissions

Check `app.log` for detailed error messages.

---

_Created with ❤️ by Atlantis Pathways_
