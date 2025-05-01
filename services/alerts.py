"""
Alert service for RTX 5090 Stock Tracker
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)

def send_email_alert(product, price, retailer_name):
    """
    Send email alert when product is in stock and under price threshold
    
    Args:
        product: Product object
        price: Current product price
        retailer_name: Name of the retailer
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL")
    to_email = os.getenv("TO_EMAIL")
    
    if not all([smtp_server, smtp_username, smtp_password, from_email, to_email]):
        logger.error("Email configuration is incomplete. Cannot send alert.")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = f"RTX 5090 In Stock Alert - {retailer_name}"
        
        body = f"""
        <html>
        <body>
            <h2>RTX 5090 In Stock Alert!</h2>
            <p>A RTX 5090 card is now available at {retailer_name}.</p>
            <p><strong>Product:</strong> {product.name}</p>
            <p><strong>Price:</strong> ${price}</p>
            <p><strong>Manufacturer:</strong> {product.manufacturer}</p>
            <p><a href="{product.url}">Click here to view the product</a></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        logger.info(f"Alert email sent for {product.name} at {retailer_name}")
    
    except Exception as e:
        logger.error(f"Error sending email alert: {e}")

def send_sms_alert(product, price, retailer_name):
    """
    Send SMS alert when product is in stock and under price threshold
    
    This is an optional feature that could be implemented using a service
    like Twilio or AWS SNS.
    
    Args:
        product: Product object
        price: Current product price
        retailer_name: Name of the retailer
    """
    # This is a placeholder for future SMS implementation
    logger.info(f"SMS alerts not yet implemented. Would have sent alert for {product.name}")
    pass