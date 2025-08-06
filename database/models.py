# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy_utils import EncryptedType
import datetime
import os

# Create a custom EncryptedType that is cache-safe to avoid SAWarning
class CachingEncryptedType(EncryptedType):
    @property
    def cache_ok(self):
        return True


# Load the encryption key from the environment.
# This key is used by EncryptedType to encrypt/decrypt data.
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")
if not DB_ENCRYPTION_KEY:
    raise ValueError("DB_ENCRYPTION_KEY not set in .env file for model encryption.")
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    name = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    email = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    password_hash = Column(String) # Passwords are hashed, not encrypted.
    is_admin = Column(Boolean, default=False)

    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    sender_config = relationship("SenderConfig", uselist=False, back_populates="user", cascade="all, delete-orphan")

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    service = Column(String)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="Idle") # e.g., Idle, Scraping, Generating, Sending, Completed, Failed
    user_id = Column(Integer, ForeignKey("users.id"))
    industries = Column(String)
    locations = Column(String) 
    platforms = Column(String) 

    user = relationship("User", back_populates="campaigns")
    leads = relationship("Lead", back_populates="campaign", cascade="all, delete-orphan")
    emails = relationship("EmailContent", back_populates="campaign", cascade="all, delete-orphan")

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    name = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    email = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    platform_source = Column(String)
    profile_link = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    website = Column(String)
    state = Column(String)
    industry = Column(String)
    profile_description = Column(CachingEncryptedType(Text, DB_ENCRYPTION_KEY))
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))

    campaign = relationship("Campaign", back_populates="leads")
    emails = relationship("EmailContent", back_populates="lead", cascade="all, delete-orphan")

class SenderConfig(Base):
    __tablename__ = "sender_configs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_name = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    sender_email = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    company_name = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    website = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    phone = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    imap_server = Column(String)
    imap_email = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))
    imap_password = Column(CachingEncryptedType(String, DB_ENCRYPTION_KEY))

    user = relationship("User", back_populates="sender_config")

class EmailContent(Base):
    __tablename__ = "email_contents"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"))
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"))
    subject = Column(CachingEncryptedType(Text, DB_ENCRYPTION_KEY))
    body = Column(CachingEncryptedType(Text, DB_ENCRYPTION_KEY))
    html = Column(CachingEncryptedType(Text, DB_ENCRYPTION_KEY))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    delivery_status = Column(String)
    opened = Column(Boolean, default=False)
    reply_text = Column(CachingEncryptedType(Text, DB_ENCRYPTION_KEY))
    reply_sentiment = Column(String)

    lead = relationship("Lead", back_populates="emails")
    campaign = relationship("Campaign", back_populates="emails")
