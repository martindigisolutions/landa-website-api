import smtplib
from email.mime.text import MIMEText
from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM

def send_email(to_email: str, subject: str, body: str):
    msg = MIMEText(body,"html")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    print(f"Sending email to {to_email} with subject '{subject}'")
    print(f"Email body: {body}")
    # Connect to the SMTP server and send the email
    print(f"Connecting to SMTP server at {EMAIL_HOST}:{EMAIL_PORT} as {EMAIL_USERNAME}")
    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    test_email = "test@example.com"
    subject = "Test Email"
    body = "<h1>This is a test email</h1><p>Sent from utils.py</p>"

    try:
        send_email(test_email, subject, body)
        print("✅ Email sent successfully.")
    except Exception as e:
        print("❌ Failed to send email:", e)
