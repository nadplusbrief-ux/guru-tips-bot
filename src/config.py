import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()  # Fallback to default search

# Bot Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
    DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "10"))
except ValueError:
    DAILY_LIMIT = 10

# Database path (stored in the parent of src directory)
DATABASE_PATH = os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "guru_tips.db"))

def validate_config():
    """Validates that all required environment variables are set."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    
    if missing:
        raise ValueError(
            f"Configuração ausente. Defina as seguintes variáveis no arquivo .env ou no ambiente: {', '.join(missing)}"
        )
