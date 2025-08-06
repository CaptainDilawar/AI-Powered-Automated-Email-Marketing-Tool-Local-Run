# 🤖 AI-Powered Automated Email Marketing Tool 
If you face any difficulty in setting up this project. Email dilawarakram13@gmail.com or Whatsapp +923016728444

This project is a full-stack, multi-user platform for running personalized cold email campaigns using AI. It features lead scraping, AI-generated emails, automated sending, open/reply tracking, and advanced analytics—all managed through a modern Streamlit dashboard.

---

## 📦 Features

- 🔐 Secure login and multi-user management
- 🛠️ **Admin Dashboard**: View all users, campaign activity, and delete users/campaigns with all related data.
- 🔍 **Lead Scraping**: Google-based lead scraping to find potential customers.
- 🧠 **AI-Generated Emails**: Utilizes Groq and LLaMA3 to create personalized emails.
- ✉️ **Automated Email Sending**: Sends emails automatically via SMTP.
- 📬 **Tracking and Analysis**: Tracks email opens and analyzes the sentiment of replies.
- 📊 **Real-Time Analytics**: View leads, sent emails, open rates, and replies in real-time.
- 📈 **Interactive Dashboard**: Includes interactive charts and a live reply viewer.
- 📂 **Data Export**: Export campaign results to CSV, Excel, or PDF.
- 🧑‍💻 **User Dashboard**: Manage sender profile, campaigns, and view results.

---

## ⚙️ Project Structure

```
.
├── .streamlit/
│   └── config.toml
├── backend/
│   ├── api.py
│   ├── analyze_replies.py
│   ├── generate_emails.py
│   ├── run_campaign.py
│   ├── scraper.py
│   └── send_emails.py
├── dashboard/
│   ├── Home.py
│   └── pages/
│       ├── AdminDashboard.py
│       ├── CreateCampaign.py
│       ├── HowItWorks.py
│       ├── Register.py
│       └── SenderSettings.py
├── database/
│   ├── db.py
│   └── models.py
├── static/
│   └── pixel.png
├── .gitignore
├── app.db
├── README.md
├── requirements.txt
├── scraper_errors.log
├── start_app.py
└── user_auth.py
```

---

## 🛠️ Setup Instructions

### 1. Install Python Dependencies

Ensure you have Python 3.10+ installed, then run:

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

First, rename the `.env.example` file to `.env`:

```bash
# On Windows
rename .env.example .env

# On macOS / Linux
mv .env.example .env
```

Next, open the `.env` file and fill in the required API keys and settings. The file contains detailed comments explaining each variable.

**Key variables you must set:**
- `GROQ_API_KEY`: For AI email generation.
- `CAPSOLVER_API_KEY`: For solving CAPTCHAs during scraping.
- `DB_ENCRYPTION_KEY`: A strong, secret key for encrypting database fields.
- `SMTP_` variables: For sending emails.
- `IMAP_` variables: For analyzing replies.

### 3. Register Users

Create new user accounts through the **Register** page on the dashboard.

### 4. Start the Application

To start the backend server and the Streamlit dashboard, run:

```bash
python start_app.py
```

The dashboard will be available at [http://localhost:8501](http://localhost:8501).

### 5. Configure Sender Profile

After logging in, navigate to **Sender Settings** and provide the following:
- Sender name
- Company name
- Email
- Website
- Phone number

### 6. Create and Manage Campaigns

From the dashboard, you can:
- Define your service or product.
- Specify target industries, locations, and platforms for lead scraping.
- Scrape leads, generate emails, send campaigns, and analyze replies.
- Monitor campaign analytics and export the results.

---

## 🚀 Workflow Overview

1.  **Lead Scraping**: Scrapes leads from Google using advanced search queries.
2.  **Email Generation**: Generates personalized emails using AI (Groq / LLaMA3).
3.  **Email Sending**: Sends emails via SMTP using the sender's configuration.
4.  **Tracking and Analysis**: Tracks email opens and analyzes reply sentiment.
5.  **Admin Oversight**: Admins can manage users and campaigns.
6.  **Data Export**: Export campaign data to CSV, Excel, or PDF.

All data is stored in the `app.db` SQLite database and managed through the dashboard and backend scripts.

---

## 🧯 Troubleshooting

- **CAPTCHA Blocking**: If you encounter a CAPTCHA, try using a VPN or wait before running the scraper again.
- **Invalid SMTP Login**: Ensure the credentials in your `.env` file are correct.
- **No Leads Scraped**: Adjust the target industries, platforms, or locations in your campaign settings.

---

## 👨‍💻 Developed by

Muhammad Dilawar Akram
