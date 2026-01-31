import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import Config

def send_email_tool(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_SENDER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(Config.EMAIL_SENDER, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

def send_task_creation_email(to_email, task_name, client, due_date):
    subject = f"New Task Assigned: {task_name}"
    body = f"""
    <h3>Task Assigned</h3>
    <p>A new task <b>'{task_name}'</b> for client <b>'{client}'</b> is due on {due_date}.</p>
    """
    return send_email_tool(to_email, subject, body)
