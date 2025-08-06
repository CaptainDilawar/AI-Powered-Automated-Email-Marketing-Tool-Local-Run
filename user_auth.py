import streamlit_authenticator as stauth
from database.db import SessionLocal
from database.models import User
import bcrypt
from dotenv import load_dotenv
import os

load_dotenv()
COOKIE_SECRET = os.getenv("COOKIE_SECRET", "a_very_secure_default_secret_key")

def get_all_users():
    session = SessionLocal()
    users = session.query(User).all()
    session.close()
    return users


def get_authenticator():
    users = get_all_users()

    # This prevents a crash on first run when the DB is empty.
    # The authenticator will simply have no users to check against.
    names = [user.name for user in users] if users else []
    usernames = [user.username for user in users] if users else []
    passwords = [user.password_hash for user in users] if users else []

    return stauth.Authenticate(
        names,
        usernames,
        passwords,
        "email_app",  # cookie name
        COOKIE_SECRET,     # secret key
        cookie_expiry_days=30
    )


def user_exists(username):
    session = SessionLocal()
    user = session.query(User).filter(User.username == username).first()
    session.close()
    return bool(user)


def is_admin_user(username):
    session = SessionLocal()
    user = session.query(User).filter(User.username == username).first()
    session.close()
    return bool(user and user.is_admin)


def add_user(name, username, password, email, is_admin=False):
    session = SessionLocal()
    try:
        # Check if username already exists
        if session.query(User).filter(User.username == username).first():
            print(f"Registration failed: Username '{username}' already exists.")
            return False

        # Check if email already exists
        if session.query(User).filter(User.email == email).first():
            print(f"Registration failed: Email '{email}' is already in use.")
            return False

        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        new_user = User(
            name=name,
            username=username,
            password_hash=hashed_pw,
            email=email,
            is_admin=is_admin
        )
        session.add(new_user)
        session.commit()
        return True
    finally:
        session.close()
