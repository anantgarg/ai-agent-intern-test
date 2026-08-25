import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEBUG_LOGGING = os.getenv("DEBUG_LOGGING", "true").lower() in {"true", "1", "yes"}