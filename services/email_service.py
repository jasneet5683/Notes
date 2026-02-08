import os
import requests
from typing import List, Optional, Dict, Any


BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def send_email_via_brevo(
    to_email: str,
    subject: str,
    html_content: str,
    *,
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """
    attachments format (Brevo):
    [
      {"content": "<base64>", "name": "file.png"}
    ]
    """
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("SENDER_EMAIL")
    sender_name = os.getenv("SENDER_NAME", "AI Assistant")

    if not api_key or not sender_email:
        return False

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    payload: Dict[str, Any] = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    if attachments:
        payload["attachment"] = attachments

    try:
        resp = requests.post(BREVO_URL, json=payload, headers=headers, timeout=20)
        return resp.status_code in (200, 201, 202)
    except requests.RequestException:
        return False
