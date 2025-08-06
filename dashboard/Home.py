import streamlit as st
import subprocess
import pandas as pd
import os
import sys
from pathlib import Path
from io import BytesIO
from xlsxwriter import Workbook
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy import text

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from user_auth import get_authenticator, is_admin_user
from database.db import SessionLocal
from database.models import User, Campaign, Lead, SenderConfig, EmailContent

st.set_page_config(page_title="📬 AI Automated Email Marketing Tool", layout="wide")

if "authenticator" not in st.session_state:
    st.session_state.authenticator = get_authenticator()

authenticator = st.session_state.authenticator
name, auth_status, username = authenticator.login("Login", "main")

if not auth_status:
    if auth_status is False:
        st.error("❌ Incorrect username or password.")
    elif auth_status is None:
        st.warning("🔐 Please enter your credentials")
    st.stop()

st.sidebar.success(f"✅ Logged in as: {username}")
if st.sidebar.button("🚪 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


import database.db as db_mod
db = SessionLocal()
user = db.query(User).filter_by(username=username).first()
if not user:
    st.error("❌ User not found in database.")
    st.stop()

admin = is_admin_user(username)

# -------------------- Admin Dashboard --------------------
if admin:
    st.title("🛠️ Admin Dashboard")
    # Use the ORM to fetch users. This is crucial because the ORM handles the
    # automatic decryption of encrypted columns like 'name' and 'email'.
    # Using a raw SQL query would fetch the raw, encrypted data.
    all_users = db.query(User).all()
    if all_users:
        # Construct a list of dictionaries to build the DataFrame correctly
        user_data = [
            {
                "username": u.username,
                "name": u.name,      # This will be decrypted by the ORM
                "email": u.email,    # This will also be decrypted
                "is_admin": u.is_admin
            } for u in all_users
        ]
        df_users = pd.DataFrame(user_data)
        st.subheader("👤 Registered Users")
        st.dataframe(df_users, use_container_width=True)

        st.subheader("📂 User Campaign Activity")
        for user_row in df_users["username"]:
            u = db.query(User).filter_by(username=user_row).first()
            if u:
                campaign_count = db.query(Campaign).filter(Campaign.user_id == u.id).count()
                # Count emails marked as "Sent"
                total_emails_sent = db.query(EmailContent).join(Campaign).filter(Campaign.user_id == u.id, EmailContent.delivery_status == "Sent").count()
                display_name = u.name if u.name else u.username
                st.markdown(f"**📂 {display_name}** — {total_emails_sent} emails sent across {campaign_count} campaigns")

        # --- Admin: Delete User Functionality ---
        st.subheader("🗑️ Delete a User")
        user_to_delete = st.selectbox("Select a user to delete", df_users["username"].tolist(), key="delete_user_select")
        if st.button("Delete Selected User", key="delete_user_btn"):
            with st.spinner(f"Deleting user '{user_to_delete}' and all related data..."):
                del_user = db.query(User).filter_by(username=user_to_delete).first()
                # With cascade="all, delete-orphan" on the User model's relationships,
                # SQLAlchemy will automatically delete all associated campaigns, leads, emails, and sender configs.
                if del_user:
                    db.delete(del_user)
                    db.commit()
                    st.success(f"✅ User '{user_to_delete}' and all related data deleted!")
                    st.rerun()
                else:
                    st.error(f"❌ User '{user_to_delete}' not found.")
    else:
        st.warning("No users registered yet.")
    # Removed st.stop() so admin can see campaign dashboard too

# -------------------- Campaign Actions --------------------

st.title(f"📬 AI Email Marketing Tool — Welcome {name}")
# Add Refresh Button
if st.button("🔄 Refresh Dashboard"):
    # Reset the action flag to re-enable buttons and hide the 'in progress' message.
    st.session_state.action_in_progress = False
    st.rerun()

# Sender Settings
st.subheader("📇 Your Sender Settings")
sender = db.query(SenderConfig).filter_by(user_id=user.id).first()
if sender:
    st.markdown(f"""
**Sender Name:** {sender.sender_name}  
**Company:** {sender.company_name}  
**Email:** {sender.sender_email}  
**Website:** {sender.website}  
**Phone:** {sender.phone}  
""")
    st.info("✏️ You can update these in the **Sender Settings** page.")
else:
    st.warning("⚠️ Sender settings not found. Please go to the **Sender Settings** page to configure.")

# Campaigns
campaigns = db.query(Campaign).filter_by(user_id=user.id).all()
if not campaigns:
    st.info("📂 No campaigns found. Run a campaign to get started.")
    st.stop()

campaign_names = [c.name for c in campaigns]

# --- State management for selected campaign to persist selection across reruns ---
# Get the index of the last selected campaign, default to 0 if not set
default_index = 0
if 'selected_campaign_name' in st.session_state:
    try:
        # Find the index of the previously selected campaign
        default_index = campaign_names.index(st.session_state.selected_campaign_name)
    except ValueError:
        # This handles cases where the campaign was deleted. Default to the first campaign.
        default_index = 0

selected_campaign = st.sidebar.selectbox("📂 Select a Campaign", campaign_names, index=default_index)
# Store the current selection in session state so it's remembered on the next rerun
st.session_state.selected_campaign_name = selected_campaign

campaign_obj = db.query(Campaign).filter_by(user_id=user.id, name=selected_campaign).first()
st.sidebar.markdown("### ⚙️ Campaign Actions")
if campaign_obj:
    
    # Display the live status of the campaign
    st.sidebar.markdown(f"**Status:** `{campaign_obj.status}`")

    # Disable buttons if a task is running.
    is_task_running = campaign_obj.status not in ["Idle", "Completed"] and not campaign_obj.status.startswith("Failed")

    import requests
    API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

    if st.sidebar.button("🔍 Scrape Leads", disabled=is_task_running):
        with st.spinner("Sending scrape request to the backend..."):
            try:
                resp = requests.post(f"{API_URL}/scrape_leads", json={"username": username, "campaign_name": selected_campaign})
                resp.raise_for_status()
                st.success("✅ Scrape task started! The browser window should appear shortly. Please refresh the dashboard in a few minutes to see the results.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Scrape failed: {e}")

    if st.sidebar.button("🧠 Generate Emails", disabled=is_task_running):
        with st.spinner("Starting email generation... This may take a moment."):
            try:
                resp = requests.post(f"{API_URL}/generate_emails", json={"username": username, "campaign_name": selected_campaign})
                resp.raise_for_status()
                st.success("✅ Email generation started! Refresh in a moment to review the email content.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to start the email task: {e}")

    if st.sidebar.button("📤 Send Generated Emails", disabled=is_task_running):
        with st.spinner("Starting email sending process..."):
            try:
                resp = requests.post(f"{API_URL}/send_emails", json={"username": username, "campaign_name": selected_campaign})
                resp.raise_for_status()
                st.success("✅ Email sending started! Refresh in a moment to see delivery statuses.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to start sending task: {e}")

    if st.sidebar.button("🔄 Re-analyze Replies", disabled=is_task_running):
        with st.spinner("Starting reply analysis..."):
            try:
                resp = requests.post(f"{API_URL}/analyze_replies", json={"username": username, "campaign_name": selected_campaign})
                st.success("✅ Reply analysis started! Please refresh the dashboard in a few minutes to see the results.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to start reply analysis: {e}")
    
else:
    st.sidebar.warning("⚠️ No campaign selected.")


if campaign_obj:
    st.markdown(f"**🛠 Service**: {campaign_obj.service} &nbsp;&nbsp; | &nbsp;&nbsp; **🗓 Date**: {campaign_obj.date_created.strftime('%Y-%m-%d')}")

    # Delete Campaign Button
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Delete This Campaign"):
        with st.spinner("Deleting campaign and all related data..."):
            # With the improved cascade settings, deleting the campaign object
            # will automatically handle the deletion of all its associated leads and emails.
            db.delete(campaign_obj)
            db.commit()
        st.success(f"✅ Campaign '{selected_campaign}' deleted!")
        st.rerun()

    # Show dashboard sections based on available data

    dashboard_mode = st.sidebar.radio("Show Data For", ["Leads", "Generated Emails", "Sent Emails", "All"], index=3)

    # --- Refactored Data Loading ---
    # We always need to join Lead and EmailContent now to get the full picture.
    # We use an outer join to ensure we still see leads even if email hasn't been generated yet.
    query = db.query(Lead, EmailContent).outerjoin(EmailContent, Lead.id == EmailContent.lead_id).filter(Lead.campaign_id == campaign_obj.id)

    if dashboard_mode == "Generated Emails":
        query = query.filter(EmailContent.id != None)
    elif dashboard_mode == "Sent Emails":
        query = query.filter(EmailContent.delivery_status == "Sent")

    results = query.all()
    data = []
    for result in results:
        lead, email = result  # Result is always a tuple now

        data.append({
            "name": lead.name,
            "email": lead.email,
            "profile_link": lead.profile_link,
            "state": lead.state,
            "industry": lead.industry,
            "platform_source": lead.platform_source,
            "profile_description": lead.profile_description,
            "email_subject": email.subject if email else None,
            "generated_email": email.body if email else None,
            "delivery_status": email.delivery_status if email else "Not Generated",
            "opened": "Yes" if email and email.opened else "No",
            "reply_text": email.reply_text if email else None,
            "reply_sentiment": email.reply_sentiment if email else None,
        })

    # st.write("[DEBUG] Raw leads data from DB:", data)
    df = pd.DataFrame(data)
    # if df.empty:
        # st.info("No data available for this mode yet.")


# -------------------- Campaign Results --------------------
if campaign_obj:

    # Always show available data for each mode, even if some steps are incomplete
    if df.empty:
        st.info("No data available for this mode yet.")
        # Don't stop, allow dashboard to show summary and export buttons (empty)

    df = df.drop_duplicates(subset=["email"])  # Remove duplicate leads by email

    st.subheader("📊 Campaign Summary")
    total_leads = len(df)
    total_sent = df["delivery_status"].eq("Sent").sum() if (not df.empty and "delivery_status" in df.columns) else 0
    total_opened = df["opened"].eq("Yes").sum() if (not df.empty and "opened" in df.columns) else 0
    replies = df["reply_text"].notna().sum() if (not df.empty and "reply_text" in df.columns) else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Leads", total_leads)
    col2.metric("Emails Sent", total_sent)
    col3.metric("Emails Opened", total_opened)
    col4.metric("Replies", replies)

    # Filters
    st.subheader("📊 Campaign Results")
    col1, col2 = st.columns(2)
    with col1:
        sentiment_filter = st.selectbox("Filter by Reply Sentiment", ["All", "Positive", "Neutral", "Negative"], key="sentiment_filter_main")
    with col2:
        opened_filter = st.selectbox("Filter by Opened Status", ["All", "Yes", "No"], key="opened_filter_main")

    filtered_df = df.copy()
    if sentiment_filter != "All":
        filtered_df = filtered_df[filtered_df["reply_sentiment"] == sentiment_filter]
    if opened_filter != "All":
        filtered_df = filtered_df[filtered_df["opened"] == opened_filter]

    st.dataframe(filtered_df, use_container_width=True)

    # Export Buttons
    st.download_button("📅 Download CSV", data=filtered_df.to_csv(index=False), file_name=f"{selected_campaign}.csv", mime="text/csv", key=f"download_csv_{dashboard_mode}")

    with BytesIO() as towrite:
        with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Report")
        towrite.seek(0)
        st.download_button("📊 Export as Excel", data=towrite.read(), file_name=f"{selected_campaign}.xlsx", key=f"download_excel_{dashboard_mode}")

    # PDF Export
    if st.button("📄 Export to PDF", key=f"export_pdf_{dashboard_mode}"):
        try:
            buffer = BytesIO()
            selected_columns = ["name", "email", "platform_source", "state", "industry", "email_subject", "reply_sentiment", "opened"]
            data = filtered_df[selected_columns].fillna("").values.tolist()
            data.insert(0, selected_columns)

            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
            style = getSampleStyleSheet()

            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#333333")),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ]))

            story = [Paragraph(f"Campaign Report: {selected_campaign}", style["Title"]), table]
            doc.build(story)

            buffer.seek(0)
            st.download_button(
                label="📄 Download Campaign Report PDF",
                data=buffer,
                file_name=f"{selected_campaign}_summary.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

    # Charts
    if "reply_sentiment" in df.columns and not df["reply_sentiment"].isnull().all():
        st.subheader("📈 Sentiment Distribution")
        st.bar_chart(df["reply_sentiment"].value_counts())

    if "opened" in df.columns and not df["opened"].isnull().all():
        st.subheader("📈 Open Rate")
        st.bar_chart(df["opened"].value_counts())

    if "reply_text" in df.columns:
        st.subheader("📬 Live Reply Viewer")
        replies = df[df["reply_text"].notna()][["email", "reply_sentiment"]]
        if not replies.empty:
            selected_email = st.selectbox("Select a reply to view", replies["email"].tolist())
            reply_text = df[df["email"] == selected_email]["reply_text"].values[0]
            st.code(reply_text, language="text")
        else:
            st.info("No replies yet.")


# -------------------- Campaign Results (for All mode) --------------------


## Removed duplicate results table and export buttons

# Close DB session
db.close()
