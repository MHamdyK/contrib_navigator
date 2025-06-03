import os
from dotenv import load_dotenv

def load_app_config():
    """Loads environment variables from .env file.""" # Corrected docstring quotes
    load_dotenv()

# Load config immediately when this module is imported
load_app_config()

# Expose specific config values
GITHUB_PAT = os.getenv("GITHUB_PAT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Add MODAL keys here later when we get to Modal setup (e.g., MODAL_TOKEN_ID, MODAL_TOKEN_SECRET if needed for scripts)

# Optional: Add checks or print statements for debugging if values are None during startup
if not GITHUB_PAT: print("WARNING: GITHUB_PAT not found in .env")
if not OPENAI_API_KEY: print("WARNING: OPENAI_API_KEY not found in .env")
