import smtplib
from email.utils import formataddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import TEST_EMAIL_ADDRESS, TEST_MODE
import logging
from socket import error as socket_error
import json

logger = logging.getLogger(__name__)

def send_email(gpt_result, row=None, sender_account=None) -> tuple:
    """Send email using GPT result (JSON string or dict). Returns (success: bool, message: str)"""
    try:
        # Parse if string
        if isinstance(gpt_result, str):
            gpt_data = json.loads(gpt_result)
        else:
            gpt_data = gpt_result
        
        # Validate sender account
        if not sender_account:
            return False, "No sender account provided"
            
    except Exception as e:
        error_msg = f"Invalid GPT result format: {e}"
        logger.error(error_msg)
        return False, error_msg

    # Default subject/body/email
    subject = gpt_data.get("subject", "")
    body = gpt_data.get("email_body", "")
    to_email = gpt_data.get("selected_email", "")

    # In test mode, override recipient and subject
    if TEST_MODE:
        to_email = TEST_EMAIL_ADDRESS
    
    # Validate configuration
    missing_config = []
    if not sender_account.get('smtp_server'): missing_config.append("SMTP_SERVER")
    if not sender_account.get('smtp_username'): missing_config.append("SMTP_USERNAME")
    if not sender_account.get('smtp_password'): missing_config.append("SMTP_PASSWORD")
    if not to_email: missing_config.append("Recipient Email")

    if missing_config:
        error_msg = f"Missing SMTP configuration: {', '.join(missing_config)}"
        logger.error(error_msg)
        return False, error_msg

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = formataddr((sender_account['name'], sender_account['email']))
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if sender_account.get('smtp_port', 465) == 465:
            # Implicit SSL
            server = smtplib.SMTP_SSL(sender_account['smtp_server'], sender_account.get('smtp_port', 465), timeout=30)
        else:
            # Explicit SSL with STARTTLS (typically port 587)
            server = smtplib.SMTP(sender_account['smtp_server'], sender_account.get('smtp_port', 587), timeout=30)
            server.starttls()

        try:
            server.login(sender_account['smtp_username'], sender_account['smtp_password'])
            server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            return True, "Email sent successfully"
            
        except smtplib.SMTPAuthenticationError:
            error_msg = "SMTP Authentication failed - check username/password"
            logger.error(error_msg)
            return False, error_msg
            
        except smtplib.SMTPException as e:
            error_msg = f"SMTP Error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except socket_error as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        finally:
            try:
                server.quit()
            except:
                pass
                
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg