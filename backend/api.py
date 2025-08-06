"""
FastAPI backend for campaign automation tasks.
Refactored from individual scripts into callable functions and API endpoints.
"""

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import traceback

# Import database and models
from database.db import SessionLocal
from database.models import User, Campaign, SenderConfig, Lead, EmailContent

import backend.scraper as scraper_mod
import backend.generate_emails as generate_emails_mod
import backend.send_emails as send_emails_mod
import backend.run_campaign as run_campaign_mod
import backend.analyze_replies as analyze_replies_mod

app = FastAPI()


# --- Request Models ---
class CampaignRequest(BaseModel):
    username: str
    campaign_name: str


# --- API Endpoints ---
@app.post("/scrape_leads")
async def api_scrape_leads(req: CampaignRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(scraper_mod.run_scraper_for_campaign, req.username, req.campaign_name)
    return {"status": "success", "message": "Scraping task has been started in the background."}

@app.post("/generate_emails")
async def api_generate_emails(req: CampaignRequest, background_tasks: BackgroundTasks):
    """Endpoint to generate email content for a campaign."""
    background_tasks.add_task(generate_emails_mod.generate_emails_for_campaign, req.username, req.campaign_name)
    return {"status": "success", "message": "Email generation has been started in the background."}

@app.post("/send_emails")
async def api_send_emails(req: CampaignRequest, background_tasks: BackgroundTasks):
    """Endpoint to send the generated emails for a campaign."""
    background_tasks.add_task(send_emails_mod.send_emails_for_campaign, req.username, req.campaign_name)
    return {"status": "success", "message": "Email sending has been started in the background."}

@app.post("/run_campaign")
async def api_run_campaign(req: CampaignRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_campaign_mod.run_campaign, req.username, req.campaign_name)
    return {"status": "success", "message": "Full campaign run has been started in the background."}

@app.post("/analyze_replies")
async def api_analyze_replies(req: CampaignRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(analyze_replies_mod.analyze_replies, req.username, req.campaign_name)
    return {"status": "success", "message": "Reply analysis has been started in the background."}


# --- Pixel Tracking Endpoint ---
from fastapi.responses import FileResponse, Response
import os

PIXEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../static/pixel.png'))

@app.get("/track_open")
async def track_open(email_id: int = None):
    if email_id:
        session = SessionLocal()
        try:
            email_content = session.query(EmailContent).filter_by(id=email_id).first()
            if email_content and not email_content.opened:
                email_content.opened = True
                session.commit()
                print(f"[TRACK] Logged open for email_id: {email_id}")
        except Exception as e:
            print(f"[TRACK] Error logging open for email_id {email_id}: {e}")
        finally:
            session.close()

    # Always serve the pixel image
    if os.path.exists(PIXEL_PATH):
        return FileResponse(PIXEL_PATH, media_type="image/png")
    else:
        return Response(content=b"", media_type="image/png")
