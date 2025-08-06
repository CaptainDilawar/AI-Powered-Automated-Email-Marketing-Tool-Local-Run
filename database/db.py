from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# --- Load Environment Variables ---
load_dotenv()
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'app.db')

# --- Database Encryption Setup ---
DB_PASSWORD = os.getenv("DB_ENCRYPTION_KEY")
if not DB_PASSWORD:
    raise ValueError("DB_ENCRYPTION_KEY not set in .env file. Please set a strong password.")

# The database file itself will not be encrypted, but sensitive columns will be,
# using the key from the environment.
DATABASE_URL = f"sqlite:///{DB_PATH}"

# 🔌 Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# 🧠 Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🧱 Base class for all models
Base = declarative_base()

# 🧰 Dependency for getting DB session (can be used in Streamlit/Flask/FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
