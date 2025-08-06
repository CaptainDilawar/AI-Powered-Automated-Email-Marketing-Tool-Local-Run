import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the refactored functions directly
import backend.scraper as scraper_mod
import backend.generate_emails as generate_emails_mod
import backend.send_emails as send_emails_mod
import backend.analyze_replies as analyze_replies_mod

def run_campaign(username: str, campaign_name: str):
    """
    Orchestrates the full campaign workflow by calling the worker functions directly.
    This is intended to be run as a background task.
    """
    print(f"\n🚀 Starting full campaign for user: {username}, campaign: {campaign_name}\n")
    
    try:
        # Step 1: Scrape Leads
        print("\n🕷️ [1/4] Running lead scraper...")
        scraper_mod.run_scraper_for_campaign(username, campaign_name)
        print("✅ Scraping completed.")

        # Step 2: Generate Emails
        print("\n🧠 [2/4] Generating emails...")
        generate_emails_mod.generate_emails_for_campaign(username, campaign_name)
        print("✅ Emails generated.")

        # Step 3: Send Emails
        print("\n📤 [3/4] Sending emails...")
        send_emails_mod.send_emails_for_campaign(username, campaign_name)
        print("✅ Emails sent.")

        # Step 4: Analyze Replies
        print("\n📬 [4/4] Analyzing replies and classifying sentiments...")
        analyze_replies_mod.analyze_replies(username, campaign_name)
        print("✅ Reply analysis complete.")
        
        print(f"\n🎉 Full campaign for '{campaign_name}' completed successfully.")
        return {"status": "success", "message": "Full campaign executed successfully."}
    except Exception as e:
        print(f"❌ Full campaign run failed for campaign '{campaign_name}': {e}")
        raise # Re-raise the exception so FastAPI logs the background task failure

def generate_and_send_emails(username: str, campaign_name: str):
    """
    Orchestrates generating and then sending emails for a campaign in the correct sequence.
    """
    print(f"\n🚀 Starting Generate & Send for user: {username}, campaign: {campaign_name}\n")
    try:
        # Step 1: Generate Emails
        print("\n🧠 [1/2] Generating emails...")
        generate_emails_mod.generate_emails_for_campaign(username, campaign_name)
        print("✅ Emails generated.")

        # Step 2: Send Emails
        print("\n📤 [2/2] Sending emails...")
        send_emails_mod.send_emails_for_campaign(username, campaign_name)
        print("✅ Emails sent.")
        
        print(f"\n🎉 Generate & Send for '{campaign_name}' completed successfully.")
    except Exception as e:
        print(f"❌ Generate & Send run failed for campaign '{campaign_name}': {e}")
        raise
