import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db import SessionLocal
from database.models import Campaign, EmailContent, Lead, User, SenderConfig

# --------- Load SMTP credentials from .env ---------
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_emails_for_campaign(username: str, campaign_name: str):
    """
    Sends all generated emails for a specific campaign.
    """
    session = SessionLocal()
    campaign_obj = None
    try:
        # Get user object
        user = session.query(User).filter_by(username=username).first()
        if not user:
            print(f"❌ User '{username}' not found in database.")
            return

        # Get sender config from DB
        sender_config = session.query(SenderConfig).filter_by(user_id=user.id).first()
        if not sender_config:
            print(f"❌ Sender config not found in database for user '{username}'")
            return

        # Set reply-to (fallback to SMTP username if empty)
        reply_to_email = sender_config.sender_email or SMTP_USERNAME

        # Get campaign
        campaign_obj = session.query(Campaign).filter_by(user_id=user.id, name=campaign_name).first()
        if not campaign_obj:
            print(f"❌ Campaign '{campaign_name}' not found for user '{username}'")
            return

        campaign_obj.status = "Sending Emails"
        session.commit()

        # Use a join to fetch both EmailContent and Lead in one query, avoiding N+1 problem.
        # Also, only fetch emails that have not been sent yet to avoid re-sending.
        emails_to_send = session.query(EmailContent, Lead).join(Lead, EmailContent.lead_id == Lead.id).filter(
            EmailContent.campaign_id == campaign_obj.id,
            (EmailContent.delivery_status == None) | (EmailContent.delivery_status != 'Sent')
        ).all()

        if not emails_to_send:
            print("⚠️ No emails found in DB to send for this campaign.")
            campaign_obj.status = "Idle"
            session.commit()
            return

        print(f"\n📤 Sending {len(emails_to_send)} emails via SMTP...\n")

        # --------- Setup SMTP server ---------
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # --------- Send Emails ---------
        for email, lead in emails_to_send:
            recipient = lead.email.strip().lower() if lead and lead.email else None

            if not recipient or "@" not in recipient:
                email.delivery_status = "Invalid Email"
                continue

            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = email.subject
                msg["From"] = SMTP_USERNAME
                msg["To"] = recipient
                msg["Reply-To"] = reply_to_email

                msg.attach(MIMEText(email.body, "plain"))
                msg.attach(MIMEText(email.html, "html"))

                server.sendmail(SMTP_USERNAME, recipient, msg.as_string())

                email.delivery_status = "Sent"
                print(f"✅ Sent to {recipient}")

            except Exception as e:
                email.delivery_status = f"Failed: {str(e)}"
                print(f"❌ Failed to {recipient} — {e}")

        session.commit()
        server.quit()
        campaign_obj.status = "Idle"
        session.commit()
        print("\n✅ All done. Email statuses saved to the database.")
    finally:
        if 'campaign_obj' in locals() and campaign_obj and session.is_active:
            if campaign_obj.status not in ["Idle", "Completed"]:
                 campaign_obj.status = "Failed: Email sending error"
                 session.commit()
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python send_emails.py <username> <campaign_name>")
        sys.exit(1)
    username_cli = sys.argv[1]
    campaign_name_cli = sys.argv[2]
    send_emails_for_campaign(username_cli, campaign_name_cli)
