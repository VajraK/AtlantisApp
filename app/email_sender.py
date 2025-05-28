import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    TEST_EMAIL_ADDRESS
)
import logging
from socket import error as socket_error

logger = logging.getLogger(__name__)

def send_email(subject: str, body: str, to_email: str = None) -> tuple:
    """Send email using SMTP. Returns (success: bool, message: str)"""
    if not to_email:
        to_email = TEST_EMAIL_ADDRESS
    
    # Validate configuration
    missing_config = []
    if not SMTP_SERVER: missing_config.append("SMTP_SERVER")
    if not SMTP_USERNAME: missing_config.append("SMTP_USERNAME")
    if not SMTP_PASSWORD: missing_config.append("SMTP_PASSWORD")
    if not to_email: missing_config.append("TEST_EMAIL_ADDRESS")
    
    if missing_config:
        error_msg = f"Missing SMTP configuration: {', '.join(missing_config)}"
        logger.error(error_msg)
        return False, error_msg

    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if SMTP_PORT == 465:
            # Implicit SSL
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        else:
            # Explicit SSL with STARTTLS (typically port 587)
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            server.starttls()

        try:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
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