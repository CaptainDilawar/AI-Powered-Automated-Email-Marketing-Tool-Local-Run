import streamlit as st

st.set_page_config(page_title="How It Works - AI Email Tool", layout="wide")

st.title("🤖 Welcome to the AI-Powered Automated Email Marketing Tool")
st.markdown("This guide explains how to use the tool to run successful cold email campaigns.")

# --- Workflow Explanation ---
st.header("🚀 Getting Started: The 5-Step Workflow")
st.markdown("""
Follow these steps to launch your campaign:
1.  **Register & Set Up**
2.  **Create a Campaign**
3.  **Scrape for Leads**
4.  **Generate & Send Emails**
5.  **Analyze Your Results**
""")

# --- Detailed Steps ---
with st.expander("Step 1: 👤 Register & Set Up Your Profile", expanded=True):
    st.markdown("""
    - **Register**: First, create an account from the **Register** page.
    - **Login**: Once registered, log in from the **Login** page.
    - **Configure Sender Settings**: Navigate to the **Sender Settings** page from the sidebar. Here, you must enter:
        - Your sender name, company, and contact details.
        - These details will be used in the emails you send.
        - **Important for Reply Analysis**: You will also need to provide your IMAP Email, IMAP Server (e.g., `imap.gmail.com`), and an **App Password** for your email account.
            - **For Gmail/Google Accounts**: If you use 2-Step Verification, you'll need to generate an App Password. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) to create one. Select 'Mail' for the app and 'Other (Custom name)' for the device, then generate the password. Use this generated password in the 'IMAP App Password' field.
            - **For Outlook/Microsoft Accounts**: You might also need to generate an App Password if you have 2-Step Verification enabled. Check your Microsoft account security settings for 'App passwords'.
            - **For Other Providers**: Consult your email provider's documentation for generating app-specific passwords or enabling IMAP access.
    """)

with st.expander("Step 2: 🎯 Create a New Campaign"):
    st.markdown("""
    - Go to the **Create Campaign** page.
    - **Define Your Campaign**: Give your campaign a unique name and describe the service you're promoting.
    - **Set Your Target**: Specify the target industries, states/locations, and platforms (like LinkedIn or Google) to find leads.
    """)

with st.expander("Step 3: 🔍 Scrape for Leads"):
    st.markdown("""
    - Once your campaign is created, it will appear in the **Select a Campaign** dropdown in the sidebar.
    - Select your campaign and click the **Scrape Leads** button.
    - The tool will start searching Google for potential leads based on your criteria.
    - You can see the scraped leads in the main dashboard view.
    """)

with st.expander("Step 4: 🧠 Generate & Send Emails"):
    st.markdown("""
    - **Generate Emails**: After scraping, click **Generate Emails**. The AI will write personalized emails for each lead.
    - **Review (Optional)**: You can review the generated emails in the dashboard.
    - **Send Emails**: Click **Send Generated Emails** to start the automated sending process.
    """)

with st.expander("Step 5: 📊 Analyze Your Results"):
    st.markdown("""
    - **Track Performance**: The main dashboard shows you real-time analytics:
        - **Leads**: Total leads scraped.
        - **Emails Sent**: How many emails have been sent.
        - **Emails Opened**: Open rates for your campaign.
        - **Replies**: The number of replies received.
    - **Analyze Replies**: Click **Re-analyze Replies** to fetch new replies and classify their sentiment (Positive, Neutral, Negative).
    - **Export Data**: You can download your campaign results as a CSV, Excel, or PDF file.
    """)

st.info("Ready to begin? Navigate to the **Register** page from the sidebar to get started.")
