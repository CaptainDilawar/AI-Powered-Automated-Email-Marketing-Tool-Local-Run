import streamlit as st
from pathlib import Path
import os
import sys

# Extend path to access database and auth
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from user_auth import get_authenticator
from database.db import SessionLocal
from database.models import SenderConfig, User

# -------------------- Page Config --------------------
st.set_page_config(page_title="✉️ Sender Settings", layout="centered")

# -------------------- Authentication --------------------
authenticator = get_authenticator()
name, auth_status, username = authenticator.login("Login", "main")

if not auth_status:
    if auth_status is False:
        st.error("❌ Incorrect username or password")
    elif auth_status is None:
        st.warning("🔐 Please enter your credentials")
    st.stop()

st.sidebar.success(f"✅ Logged in as: {username}")
authenticator.logout("🚪 Logout", "sidebar")

# -------------------- DB Session --------------------
db = SessionLocal()
user = db.query(User).filter_by(username=username).first()
if not user:
    st.error("❌ User not found in database.")
    st.stop()

# -------------------- Load Existing Config --------------------
sender_config = db.query(SenderConfig).filter_by(user_id=user.id).first()

# -------------------- Sender Settings Form --------------------
st.title("✉️ Customize Your Sender Identity")
st.markdown("Fill in the details below to personalize your email campaigns.")

with st.form("sender_form"):
    company_name = st.text_input("Company Name", value=sender_config.company_name if sender_config else "")
    sender_name = st.text_input("Sender Name", value=sender_config.sender_name if sender_config else "")
    sender_email = st.text_input("Sender Email", value=sender_config.sender_email if sender_config else "")
    website = st.text_input("Website URL", value=sender_config.website if sender_config else "")
    phone = st.text_input("Phone Number", value=sender_config.phone if sender_config else "")

    st.markdown("### IMAP Settings for Reply Analysis")
    imap_server = st.text_input("IMAP Server", value=sender_config.imap_server if sender_config else "imap.gmail.com")
    imap_email = st.text_input("IMAP Email", value=sender_config.imap_email if sender_config else "")
    imap_password = st.text_input("IMAP App Password", type="password", value=sender_config.imap_password if sender_config else "")

    submitted = st.form_submit_button("💾 Save Settings")

    if submitted:
        if sender_config:
            # Update existing config
            sender_config.company_name = company_name.strip()
            sender_config.sender_name = sender_name.strip()
            sender_config.sender_email = sender_email.strip()
            sender_config.website = website.strip()
            sender_config.phone = phone.strip()
            sender_config.imap_server = imap_server.strip()
            sender_config.imap_email = imap_email.strip()
            sender_config.imap_password = imap_password
        else:
            # Create new config
            sender_config = SenderConfig(
                user_id=user.id,
                company_name=company_name.strip(),
                sender_name=sender_name.strip(),
                sender_email=sender_email.strip(),
                website=website.strip(),
                phone=phone.strip(),
                imap_server=imap_server.strip(),
                imap_email=imap_email.strip(),
                imap_password=imap_password
            )
            db.add(sender_config)

        db.commit()
        st.success("✅ Sender settings saved successfully!")
        st.balloons()

# -------------------- Show Preview --------------------
if sender_config:
    st.markdown("---")
    st.subheader("📋 Current Sender Identity")
    st.json({
        "company_name": sender_config.company_name,
        "sender_name": sender_config.sender_name,
        "sender_email": sender_config.sender_email,
        "website": sender_config.website,
        "phone": sender_config.phone
    })

# -------------------- Close DB --------------------
db.close()
