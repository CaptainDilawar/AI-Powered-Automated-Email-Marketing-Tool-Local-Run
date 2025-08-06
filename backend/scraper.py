print("=== Scraper started ===", flush=True)
import sys
import os
import json
import time
import random
import re
import requests
import base64
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from itertools import product
import logging
import capsolver
from dotenv import load_dotenv

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database.db import SessionLocal
from database.models import User, Campaign, SenderConfig, Lead

# --------- Constants ---------
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
]

DORK_PATTERNS = [
    'site:{site_domain} "{industry}" "{location}" "@gmail.com"',
    'site:{site_domain} "{industry}" "{location}" intext:email',
    'site:{site_domain} "{industry}" "{location}" contact',
    'site:{site_domain} "{industry}" "{location}" "contact us"',
    'site:{site_domain} "{industry}" "{location}" inurl:contact',
    'site:{site_domain} "{industry}" "{location}" intitle:contact',
    'site:{site_domain} "{industry}" "{location}" "@yahoo.com"',
    'site:{site_domain} "{industry}" "{location}" "@outlook.com"'
]

# Load environment variables from .env file
load_dotenv()

# Access the API key and set it for the capsolver library
capsolver.api_key = os.getenv("CAPSOLVER_API_KEY")


# --------- Utility Functions ---------

def has_website(text):
    return bool(re.search(r"https?://[\w.-]+|www\.[\w.-]+", text))

def is_captcha_present(driver):
    """
    ### FINAL VERSION - Detects reCAPTCHA v2 ###
    Detects the "I'm not a robot" reCAPTCHA v2 by looking for its specific iframe.
    This is the most reliable method for the CAPTCHA in your screenshot.
    """
    try:
        # A short wait is enough to see if the iframe is present.
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/anchor']"))
        )
        return True
    except TimeoutException:
        return False

def solve_recaptcha(driver):
    """
    ### FINAL VERSION - Solves reCAPTCHA v2 ###
    Solves the Google reCAPTCHA v2 using Capsolver's ReCaptchaV2TaskProxyless.
    """
    print("[CAPTCHA] reCAPTCHA v2 detected. Solving with Capsolver...")
    try:
        # 1. Extract the sitekey from the g-recaptcha div element on the page.
        recaptcha_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "g-recaptcha"))
        )
        sitekey = recaptcha_element.get_attribute("data-sitekey")
        
        if not sitekey:
            print("[CAPTCHA] FATAL: Could not find the reCAPTCHA sitekey on the page.")
            return False

        print(f"[CAPTCHA] Sitekey found: {sitekey}")
        
        # 2. Create the task on Capsolver with the correct type.
        solution = capsolver.solve({
            "type": "ReCaptchaV2TaskProxyless",
            "websiteURL": driver.current_url,
            "websiteKey": sitekey
        })
        
        recaptcha_token = solution.get("gRecaptchaResponse")
        if not recaptcha_token:
            print("[CAPTCHA] FAILED: Capsolver did not return a solution token.")
            print(f"[CAPTCHA] Full response from Capsolver: {solution}")
            return False
            
        print("[CAPTCHA] Solution token received from Capsolver.")

        # 3. Inject the solution token into the hidden textarea element.
        driver.execute_script(
            f"document.getElementById('g-recaptcha-response').innerHTML = '{recaptcha_token}';"
        )
        print("[CAPTCHA] Injected solution token into the page.")
        
        # 4. Find and click the submit button.
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"))
        )
        submit_button.click()
        print("[CAPTCHA] Submit button clicked.")

        # 5. Wait and verify that we have successfully left the CAPTCHA page.
        time.sleep(5)
        if "sorry/index" in driver.current_url:
            print("[CAPTCHA] FAILED. Still on CAPTCHA page after submission.")
            return False
        else:
            print("[CAPTCHA] SUCCESS! CAPTCHA appears to be solved.")
            return True

    except Exception as e:
        print(f"[CAPTCHA] An unexpected error occurred during reCAPTCHA solving: {e}")
        return False

def scrape_google(combinations):
    """
    Initializes a headless Selenium driver and scrapes Google for leads.
    """
    # Setup robust browser options for a server environment
    options = Options()
    # options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1200")
    # options.add_argument("--disable-features=SignInPromoUI") # Prevents the Chrome sign-in popup
    options.add_argument("--disable-blink-features=AutomationControlled") # Helps avoid bot detection
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Suppress console logs from Selenium
    service = Service(log_path=os.devnull)
    logging.getLogger('selenium').setLevel(logging.CRITICAL)

    try:
        driver = webdriver.Chrome(service=service, options=options)
    except WebDriverException as e:
        print(f"❌ Failed to start WebDriver: {e}. Ensure Chrome/ChromeDriver are installed and compatible.")
        return []

    leads = []
    email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"
    for platform, industry, location in combinations:
        site_domain = platform if '.' in platform else f"{platform}.com"
        for dork in DORK_PATTERNS:
            query = dork.format(site_domain=site_domain, industry=industry, location=location)
            print(f"[SEARCH] {query}")
            try:
                # Set a realistic user agent for each request
                driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": random.choice(USER_AGENTS)})
                driver.get("https://www.google.com/search?q=" + requests.utils.quote(query))
                
                # Check for and solve the reCAPTCHA if it appears
                if is_captcha_present(driver):
                    if not solve_recaptcha(driver):
                        print("[INFO] Skipping query due to failed CAPTCHA.")
                        continue # Move to the next dork
                
                # Proceed to scrape results
                results = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.tF2Cxc, div.g"))
                )

                for result in results:
                    try:
                        title = result.find_element(By.CSS_SELECTOR, "h3").text
                        link = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                        
                        description = ""
                        try:
                            description = result.find_element(By.CSS_SELECTOR, "div.VwiC3b, span.st").text
                        except NoSuchElementException:
                            pass

                        emails = set(re.findall(email_pattern, description))
                        
                        try:
                            resp = requests.get(link, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=7)
                            if resp.status_code == 200:
                                page_emails = set(re.findall(email_pattern, resp.text))
                                emails.update(page_emails)
                        except Exception:
                            pass

                        if emails:
                            for email in emails:
                                leads.append({
                                    "name": title,
                                    "email": email.strip().lower(),
                                    "platform_source": platform.capitalize(),
                                    "profile_link": link,
                                    "state": location,
                                    "industry": industry,
                                    "profile_description": "" 
                                })
                    except Exception as e:
                        print(f"Error parsing an individual result: {e}")
                        continue
                
                # Wait a bit before the next search to avoid being blocked
                time.sleep(random.uniform(4, 7))

            except Exception as e:
                print(f"[ERROR] A critical error occurred in the main search loop: {e}")
                driver.save_screenshot('error_screenshot.png') # Helpful for debugging
                continue
    driver.quit()
    print(f"Total leads found: {len(leads)}")
    return leads

def run_scraper_for_campaign(username: str, campaign_name: str):
    """
    Main task function that connects to the DB and runs the scraper.
    """
    session = SessionLocal()
    campaign_obj = None
    try:
        print(f"[TASK] Starting for user '{username}', campaign '{campaign_name}'")
        user_obj = session.query(User).filter_by(username=username).first()
        if not user_obj:
            raise Exception(f"User '{username}' not found.")
        campaign_obj = session.query(Campaign).filter_by(user_id=user_obj.id, name=campaign_name).first()
        if not campaign_obj:
            raise Exception(f"Campaign '{campaign_name}' not found for user.")

        campaign_obj.status = "Scraping"
        session.commit()
        
        platforms = campaign_obj.platforms.split(",")
        industries = campaign_obj.industries.split(",")
        locations = campaign_obj.locations.split(",")
        combinations = list(product(platforms, industries, locations))

        leads_data = scrape_google(combinations)
        
        if leads_data:
            existing_emails = {lead.email for lead in campaign_obj.leads}
            new_leads_added = 0
            for lead_dict in leads_data:
                if lead_dict["email"] not in existing_emails:
                    new_lead = Lead(**lead_dict, campaign_id=campaign_obj.id)
                    session.add(new_lead)
                    existing_emails.add(new_lead.email)
                    new_leads_added += 1
            if new_leads_added > 0:
                print(f"[TASK] SUCCESS: Saved {new_leads_added} new leads for campaign '{campaign_name}'.")
                session.commit()
            else:
                print(f"[TASK] INFO: Scraped {len(leads_data)} leads, but all were duplicates.")
        else:
            print("[TASK] INFO: Scraper finished with no new leads found.")
            
        campaign_obj.status = "Idle"
        session.commit()
    except Exception as e:
        print(f"[TASK] FAILED for campaign '{campaign_name}': {e}")
        if campaign_obj:
            campaign_obj.status = "Failed: Scraping error"
            session.commit()
        session.rollback()
    finally:
        session.close()

# --------- Main Execution Block ---------
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scraper.py <username> <campaign_name>")
        sys.exit(1)

    if not capsolver.api_key:
        print("CRITICAL ERROR: CAPSOLVER_API_KEY is not set. Please create a .env file or set an environment variable.")
        sys.exit(1)
        
    username_cli = sys.argv[1]
    campaign_name_cli = sys.argv[2]
    run_scraper_for_campaign(username_cli, campaign_name_cli)