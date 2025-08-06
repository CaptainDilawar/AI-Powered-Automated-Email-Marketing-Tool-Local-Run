import pandas as pd
import requests
from tqdm import tqdm
import os
import json
from dotenv import load_dotenv
import csv
import sys
from pathlib import Path
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database.db import SessionLocal
from database.models import Campaign, Lead, EmailContent, User
# Folder creation removed; all data is stored in the database
# --------- Load API Key ---------
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --------- Load Sender Info (User-specific) ---------


# --------- Industry Role Mapping ---------
INDUSTRY_ROLES = {
    "Real Estate": "Real Estate Manager",
    "Clinic": "Clinic Manager",
    "Law Firm": "Legal Advisor",
    "Restaurant": "Restaurant Owner",
    "E-commerce": "E-commerce Owner",
    "Fitness": "Gym Owner",
    "Education": "School Administrator"
}

def create_prompt(row, sender_info, service="Website Development"):
    # Sender details from user config
    company_name = sender_info["company_name"]
    sender_name = sender_info["sender_name"]
    sender_email = sender_info["sender_email"]
    website = sender_info["website"]
    phone = sender_info["phone"]

    # Lead details
    industry = row['Industry']
    state = row['State']
    platform = row['Platform Source']
    description = str(row.get('Profile Description', '') or '').strip()

    role_title = INDUSTRY_ROLES.get(industry, f"{industry} Professional")
    title_with_location = f"{role_title} in {state}"

    prompt = f"""
You are a professional email copywriter working for a digital agency called {company_name}. 

Your goal is to help generate leads for the agency by reaching out to potential clients for {service} services.

Generate:
1. A compelling subject line (less than 10 words)
2. A short, personalized outreach email.

Details:
- Recipient: {title_with_location}
- Industry: {industry}
- State: {state}
- Source Platform: {platform}
- Profile Description: "{description or 'N/A'}"

The email should:
- Mention they don't have a website
- Be personalized to their industry and location
- Be friendly, professional, and concise
- Start the email with: "Hi {title_with_location},"
- Include a call to action (e.g., "Can we connect for a quick chat?")
- End with this signature:

Best,  
{sender_name}  
{company_name}  
📧 {sender_email}  
🌐 {website}  
📞 {phone}

Return the output in this format:
Subject: [subject]  
Email:  
[email body]
"""
    return prompt.strip()

def generate_from_groq(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a professional email copywriter."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 600
    }

    for attempt in range(3):
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
            result = r.json()

            if "error" in result and "rate_limit_exceeded" in result.get("error", {}).get("code", ""):
                wait_time = 5 * (attempt + 1)
                print(f"⏳ Rate limit hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            if "choices" not in result or not result["choices"]:
                print("❌ Unexpected API response format:", result)
                return "ERROR", "ERROR"

            content = result["choices"][0]["message"]["content"].strip()

            subject = "N/A"
            body = content
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if line.lower().startswith("subject:"):
                    subject = line.replace("Subject:", "").strip()
                elif line.lower().startswith("email:"):
                    body = "\n".join(lines[i+1:]).strip()
                    break

            return subject, body

        except Exception as e:
            print(f"❌ Groq API error: {e}")
            time.sleep(3)

    return "ERROR", "ERROR"

def convert_to_html(text, email_id):
    lines = text.strip().splitlines()
    html = "<p>" + "</p><p>".join(line.strip() for line in lines if line.strip()) + "</p>"
    # The tracking endpoint is now part of the FastAPI app on port 8000
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    tracking_pixel = f'<img src="{api_base_url}/track_open?email_id={email_id}" width="1" height="1" alt="" style="display:none;">'
    return html + tracking_pixel

def generate_emails_for_campaign(username: str, campaign_name: str):
    """
    Generates email content for all leads in a specific campaign for a given user.
    It will first delete any existing email content for the campaign.
    """
    session = SessionLocal()
    campaign_obj = None
    try:
        # --- Fetch user object first ---
        user_obj = session.query(User).filter_by(username=username).first()
        if not user_obj:
            print(f"❌ User '{username}' not found.")
            return

        # --- Fetch sender config from DB ---
        from database.models import SenderConfig
        sender_config = session.query(SenderConfig).filter_by(user_id=user_obj.id).first()
        if not sender_config:
            print(f"❌ Sender config not found for user '{username}'. Please set it from the Sender Settings UI.")
            return

        sender_info = {
            "company_name": sender_config.company_name,
            "sender_name": sender_config.sender_name,
            "sender_email": sender_config.sender_email,
            "website": sender_config.website,
            "phone": sender_config.phone
        }

        # --- Fetch campaign using user_id ---
        campaign_obj = session.query(Campaign).filter_by(user_id=user_obj.id, name=campaign_name).first()
        if not campaign_obj:
            print(f"❌ Campaign '{campaign_name}' not found for user '{username}'")
            return

        campaign_obj.status = "Generating Emails"
        session.commit()

        # --- Delete existing emails for this campaign ---
        print(f"🗑️ Deleting existing email content for campaign '{campaign_name}'...")
        session.query(EmailContent).filter_by(campaign_id=campaign_obj.id).delete()
        session.commit()
        print("✅ Existing content deleted.")

        all_leads = session.query(Lead).filter_by(campaign_id=campaign_obj.id).all()
        if not all_leads:
            print("⚠️ No leads found in database for this campaign.")
            campaign_obj.status = "Idle"
            session.commit()
            return

        print(f"\n📬 Generating emails using Groq API for {len(all_leads)} leads...\n")

        for lead in tqdm(all_leads):
            prompt = create_prompt({
                "Industry": lead.industry,
                "State": lead.state,
                "Platform Source": lead.platform_source,
                "Profile Description": lead.profile_description
            }, sender_info)
            subject, email = generate_from_groq(prompt)

            # Create a placeholder first to get an ID
            email_content = EmailContent(
                lead_id=lead.id,
                campaign_id=campaign_obj.id,
                subject=subject,
                body=email
            )
            session.add(email_content)
            session.flush()  # Assigns an ID to email_content without committing

            # Now generate HTML with the correct ID and update the object
            email_html = convert_to_html(email, email_id=email_content.id)
            email_content.html = email_html

        session.commit()
        campaign_obj.status = "Idle"
        session.commit()
        print("\n✅ Emails saved to database.")
    finally:
        if 'campaign_obj' in locals() and campaign_obj and session.is_active:
            if campaign_obj.status not in ["Idle", "Completed"]:
                 campaign_obj.status = "Failed: Email generation error"
                 session.commit()
        session.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_emails.py <username> <campaign_name>")
        sys.exit(1)
    username_cli = sys.argv[1]
    campaign_name_cli = sys.argv[2]
    generate_emails_for_campaign(username_cli, campaign_name_cli)
