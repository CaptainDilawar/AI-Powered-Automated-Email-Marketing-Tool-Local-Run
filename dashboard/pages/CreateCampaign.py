import streamlit as st
import os
import sys
from pathlib import Path
from sqlalchemy.exc import IntegrityError

# Extend path to access database and auth
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from database.db import SessionLocal
from database.models import Campaign
from user_auth import get_authenticator
from database.models import User

# -------------------- Page Setup --------------------
st.set_page_config(page_title="🎯 Create Campaign", layout="centered")
st.title("🎯 Create a New Campaign")

# -------------------- Authentication --------------------
authenticator = get_authenticator()
name, auth_status, username = authenticator.login("Login", "main")

if not auth_status:
    if auth_status is False:
        st.error("❌ Incorrect username or password")
    elif auth_status is None:
        st.warning("🔐 Please log in to access this page.")
    st.stop()

st.sidebar.success(f"✅ Logged in as: {username}")
authenticator.logout("🚪 Logout", "sidebar")

# -------------------- Form --------------------
with st.form("create_campaign"):
    campaign_name = st.text_input("Campaign Name (no spaces)", max_chars=30)
    service = st.text_input("Service You're Offering", value="Website Development")
    industries = st.multiselect(
        "Select Target Industries",
        ["Real Estate", "Clinic", "Law Firm", "Restaurant", "E-commerce", "Fitness", "Education"]
    )
    locations = st.text_input("Target Locations (comma-separated)", value="California, Texas, Florida")
    platforms = st.multiselect(
        "Platforms to Target",
        ["instagram", "yelp", "linkedin", "google"]
    )

    submitted = st.form_submit_button("📦 Save Campaign")

# -------------------- Save to DB --------------------
if submitted:
    if not campaign_name:
        st.warning("⚠️ Please enter a campaign name.")
    elif not industries or not platforms:
        st.warning("⚠️ Select at least one industry and one platform.")
    else:
        clean_name = campaign_name.strip().replace(" ", "_").lower()
        db = SessionLocal()

        try:
            user = db.query(User).filter_by(username=username).first()
            if not user:
                st.error("❌ Logged-in user not found in database.")
            else:
                new_campaign = Campaign(
                    name=clean_name,
                    service=service.strip(),
                    user_id=user.id,
                    industries=",".join(industries),
                    locations=",".join([loc.strip() for loc in locations.split(",")]),
                    platforms=",".join(platforms)
                )
                db.add(new_campaign)
                db.commit()

                st.success(f"✅ Campaign '{clean_name}' created!")
                st.balloons()

        except IntegrityError:
            db.rollback()
            st.error(f"❌ A campaign named '{clean_name}' already exists.")

        finally:
            db.close()
