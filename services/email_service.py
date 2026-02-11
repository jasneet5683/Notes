import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import os

# Load Config
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL")

def send_email_via_brevo(subject: str, email_body: str, recipient_email: str = None) -> str:
    """
    Sends an email using Brevo API.
    """
    if not BREVO_API_KEY:
        return "❌ Error: BREVO_API_KEY is missing."

    # If AI doesn't provide a recipient, use the default admin
    if not recipient_email:
        recipient_email = DEFAULT_ADMIN_EMAIL

    # Configure API key authorization
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    # Create Email Object
    sender = {"name": "AI Project Manager", "email": SENDER_EMAIL}
    to = [{"email": recipient_email}]
    
    # We use HTML content for better formatting
    html_content = f"""
    <html>
    <body>
        <h3>{subject}</h3>
        <p>{email_body.replace(chr(10), '<br>')}</p>
        <br>
        <hr>
        <small>Sent via AI Project Assistant</small>
    </body>
    </html>
    """

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to,
        sender=sender,
        subject=subject,
        html_content=html_content
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        return f"✅ Email sent successfully to {recipient_email}."
    except ApiException as e:
        print(f"❌ Brevo Error: {e}")
        return f"❌ Failed to send email: {e}"
