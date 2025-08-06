import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from pathlib import Path
from user_auth import add_user, user_exists, get_authenticator

st.set_page_config(page_title="📝 Register", layout="centered")
st.title("📝 Create Your Account")

# Navigation: Back to login
if st.button("🔙 Back to Login"):
    # Only works when app is launched from Home.py at root
    st.switch_page("Home.py")

with st.form("register"):
    name = st.text_input("Full Name")
    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm = st.text_input("Confirm Password", type="password")
    submit = st.form_submit_button("Register")

    if submit:
        if not name or not username or not email or not password:
            st.warning("⚠️ Please fill out all fields.")
        elif user_exists(username):
            st.error("❌ Username already exists.")
        elif password != confirm:
            st.error("❌ Passwords do not match.")
        elif len(password) < 6:
            st.warning("🔐 Password should be at least 6 characters.")
        else:
            if add_user(name, username, password, email):
                st.success("✅ Registered successfully! Please log in.")
                st.balloons()
                # Clear session state to ensure previous user is logged out
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.switch_page("Home.py")
            else:
                # Since we already check for username, this error must be for the email
                st.error("❌ Email is already in use.")
