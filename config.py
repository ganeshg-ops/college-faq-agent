import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
UNANSWERED_QUESTIONS_FILE = DATA_DIR / "unanswered_questions.json"
QUERY_HISTORY_FILE = DATA_DIR / "query_history.json"
STUDENTS_FILE = DATA_DIR / "students.json"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

# Ensure essential directories exist
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Default to gemini-2.5-flash or gemini-1.5-flash
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Institution Branding
COLLEGE_NAME = os.getenv("COLLEGE_NAME", "AMMAN GROUP OF INSTITUTIONS")

# Admin Security
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_SESSION_KEY = "is_admin_authenticated"

# Document & Retrieval Settings
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".json"}
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "25"))
CHUNK_SIZE_CHARS = int(os.getenv("CHUNK_SIZE_CHARS", "1000"))
CHUNK_OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "150"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "4"))
MIN_RELEVANCE_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.20"))
