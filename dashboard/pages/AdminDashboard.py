import pandas as pd
import os
import sys
from pathlib import Path
import streamlit as st

# Allow import from root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from user_auth import get_authenticator, is_admin_user

# Import DB session and models
from database.db import SessionLocal
from database.models import User, Campaign, EmailContent, Lead

# Page config
st.set_page_config(page_title="🛠️ Admin Dashboard", layout="wide")

# --- Authenticate first ---
authenticator = get_authenticator()

# Always show login form if not authenticated
name, auth_status, username = authenticator.login("Login", "main")

if auth_status is None:
    st.warning("🔐 Please log in to access this page.")
    st.stop()
elif auth_status is False:
    st.error("❌ Incorrect username or password.")
    st.stop()

# --- Check admin role ---
if not is_admin_user(username):
    st.error("🚫 You do not have access to this page. Please log in as an administrator.")
    if st.button("🔑 Login as Admin"):
        st.switch_page("Home.py")
    st.stop()

st.sidebar.success(f"✅ Logged in as admin: {username}")
authenticator.logout("🚪 Logout", "sidebar")

# --- Admin dashboard content ---
st.title("🛠️ Admin Dashboard")

db = SessionLocal()

# --- Show registered users ---
st.subheader("👤 Registered Users")

users = db.query(User).all()
if users:
    user_data = [{
        "Name": u.name,
        "Username": u.username,
        "Email": u.email,
        "Is Admin": "Yes" if u.is_admin else "No"
    } for u in users]

    df_users = pd.DataFrame(user_data)
    st.dataframe(df_users, use_container_width=True)
else:
    st.info("No users registered yet.")

# --- Show campaign + email summary from DB ---
st.subheader("📂 User Campaign Summary")

campaigns = db.query(Campaign).all()
if not campaigns:
    st.info("No campaigns found.")
else:
    summary = {}
    for c in campaigns:
        key = c.user
        summary.setdefault(key, {"campaigns": 0, "emails": 0})
        summary[key]["campaigns"] += 1
        email_count = (
            db.query(EmailContent)
            .join(Lead, EmailContent.lead_id == Lead.id)
            .join(Campaign, Lead.campaign_id == Campaign.id)
            .filter(Campaign.user_id == c.user_id, Campaign.name == c.name)
            .count()
        )
        summary[key]["emails"] += email_count

    for user, stats in summary.items():
        display_name = user.name if hasattr(user, 'name') and user.name else (user.username if hasattr(user, 'username') else str(user))
        st.markdown(
            f"**🗂️ {display_name}** — {stats['emails']} emails sent across {stats['campaigns']} campaign(s)"
        )

db.close()
