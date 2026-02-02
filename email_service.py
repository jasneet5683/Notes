import os
import requests
from config import Config

def send_email_via_brevo(to_email, subject, body):
    """
    Sends an email using the Brevo API.
    """
    if not Config.BREVO_API_KEY:
        return {"status": "error", "message": "Missing BREVO_API_KEY"}

    url = "https://api.brevo.com/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "api-key": Config.BREVO_API_KEY,
        "content-type": "application/json"
    }
    
    payload = {
        "sender": {
            "name": Config.SENDER_NAME,
            "email": Config.SENDER_EMAIL
        },
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": f"<p>{body}</p>"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 201:
            return {"status": "success", "message": f"Email sent to {to_email}"}
        else:
            return {"status": "error", "message": f"Brevo Error: {response.text}"}
            
    except Exception as e:
        return {"status": "error", "message": f"Exception: {str(e)}"}
