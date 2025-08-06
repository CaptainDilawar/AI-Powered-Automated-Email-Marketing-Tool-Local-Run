import subprocess
import time
import os
from database.db import engine
from database.models import Base

# Ensure database tables exist
Base.metadata.create_all(bind=engine)
ROOT = os.path.dirname(os.path.abspath(__file__))
print(f"🌍 Project root directory: {ROOT}")

if __name__ == "__main__":
    print("🚀 Starting FastAPI backend...")
    # Use subprocess.Popen to run servers as independent processes
    # This allows Uvicorn's reloader to work correctly without threading issues
    fastapi_process = subprocess.Popen(
        ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    )

    print("📊 Launching Streamlit dashboard...")
    streamlit_process = subprocess.Popen(
        ["streamlit", "run", os.path.join(ROOT, 'dashboard', 'Home.py'), "--server.port", "8501"]
    )

    print("\n✅ System running. Use Ctrl+C to shut down.")
    try:
        # Keep the main script alive to manage the subprocesses
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
        fastapi_process.terminate()
        streamlit_process.terminate()
        print("✅ Shutdown complete.")