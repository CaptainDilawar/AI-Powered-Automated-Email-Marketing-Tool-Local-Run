import os
import requests
from pathlib import Path
from imapclient import IMAPClient
import pyzmail
import sys

# Add root path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database.db import SessionLocal
from database.models import Campaign, EmailContent, Lead, User, SenderConfig

# --------- Load Environment Variables (only GROQ_API_KEY remains global) ---------
# IMAP credentials are now fetched per-user from SenderConfig
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# --------- Sentiment Classifier ---------
def classify_reply_text(reply_text):
    prompt = f"""You are a sales assistant. Classify the following email reply into one of the following categories:
- Positive (interested or wants to connect)
- Neutral (asks for more info or ambiguous)
- Negative (not interested, unsubscribe, or rejection)

Reply:
{reply_text}

Just return: Positive, Neutral, or Negative.
"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a professional email assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 100
    }

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
        r.raise_for_status()
        result = r.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"❌ Error classifying reply: {e}")
        return "Unknown"


# --------- Analyze Replies ---------
def analyze_replies(username, campaign_name):
    session = SessionLocal()
    campaign_obj = None

    # Fetch user object
    user_obj = session.query(User).filter_by(username=username).first()
    if not user_obj:
        print(f"❌ User '{username}' not found.")
        return

    # Fetch campaign
    campaign_obj = session.query(Campaign).filter_by(user_id=user_obj.id, name=campaign_name).first()
    if not campaign_obj:
        print(f"❌ Campaign '{campaign_name}' not found for user '{username}'")
        return

    campaign_obj.status = "Analyzing Replies"
    session.commit()

    # Use a join to fetch both EmailContent and Lead in one query, avoiding N+1 problem.
    email_lead_pairs = session.query(EmailContent, Lead).join(Lead, EmailContent.lead_id == Lead.id).filter(EmailContent.campaign_id == campaign_obj.id).all()
    if not email_lead_pairs:
        campaign_obj.status = "Idle"
        session.commit()

        print(f"⚠️ No emails found for campaign '{campaign_name}'")
        return

    # Map recipient emails to their records
    lead_map = {}
    for email_record, lead_record in email_lead_pairs:
        if lead_record and lead_record.email:
            lead_map[lead_record.email.lower()] = (email_record, lead_record)

    if not lead_map:
        campaign_obj.status = "Idle"
        session.commit()
        print("⚠️ No leads with valid email addresses found.")
        return


    # Fetch user's sender config for IMAP credentials
    sender_config = session.query(SenderConfig).filter_by(user_id=user_obj.id).first()
    if not sender_config or not sender_config.imap_email or not sender_config.imap_password or not sender_config.imap_server:
        print(f"❌ IMAP credentials not configured for user '{username}'. Please update Sender Settings.")
        campaign_obj.status = "Idle"
        session.commit()
        return

    IMAP_EMAIL = sender_config.imap_email
    IMAP_PASSWORD = sender_config.imap_password
    IMAP_SERVER = sender_config.imap_server

    # Connect to IMAP
    with IMAPClient(IMAP_SERVER) as client:
        try:
            client.login(IMAP_EMAIL, IMAP_PASSWORD)
        except Exception as e:
            print(f"❌ Failed to log in to IMAP server for user '{username}': {e}")
            campaign_obj.status = "Failed"
            session.commit()
            return
        client.select_folder('INBOX', readonly=False)

        all_uids = set()
        for addr in lead_map.keys():
            try:
                uids = client.search(['FROM', addr])
                all_uids.update(uids)
            except Exception as e:
                print(f"IMAP search failed for sender {addr}: {e}", flush=True)

        if not all_uids:
            print("✅ No new replies found in the inbox for this campaign's leads.")
            campaign_obj.status = "Idle"
            session.commit()
            session.close()
            return

        for uid in all_uids:
            raw = client.fetch([uid], ['BODY[]', 'ENVELOPE'])
            msg = pyzmail.PyzMessage.factory(raw[uid][b'BODY[]'])
            envelope = raw[uid][b'ENVELOPE']
            sender_email = envelope.from_[0].mailbox.decode() + '@' + envelope.from_[0].host.decode()

            email_entry = lead_map.get(sender_email.lower())
            if not email_entry:
                print(f"⚠️ Reply from unknown sender: {sender_email}")
                continue

            email_record, _ = email_entry

            if msg.text_part:
                try:
                    reply_text = msg.text_part.get_payload().decode(msg.text_part.charset)
                    sentiment = classify_reply_text(reply_text)
                    email_record.reply_text = reply_text
                    email_record.reply_sentiment = sentiment
                    print(f"✅ Reply from {sender_email} → {sentiment}")
                except Exception as e:
                    print(f"⚠️ Error decoding reply from {sender_email}: {e}")

    session.commit()
    campaign_obj.status = "Idle"
    session.commit()
    session.close()
    print("\n✅ Replies analyzed and saved to DB.")


# --------- CLI Entry Point ---------
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python analyze_replies.py <username> <campaign>")
        sys.exit(1)

    username = sys.argv[1]
    campaign = sys.argv[2]
    analyze_replies(username, campaign)
