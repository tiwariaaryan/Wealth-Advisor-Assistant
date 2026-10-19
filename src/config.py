import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = BASE_DIR / "memory_store"
MEMORY_DIR.mkdir(exist_ok=True)

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

class Config:
    # Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Paths to data
    SAMPLE_CLIENTS_PATH: Path = DATA_DIR / "sample_clients.json"
    MOCK_CRM_PATH: Path = DATA_DIR / "mock_crm_db.json"
    LONG_TERM_MEMORY_PATH: Path = MEMORY_DIR / "historical_memory.json"

    # Financial & Anomaly Thresholds
    CASH_DRAG_THRESHOLD_PERCENT: float = 20.0  # Flag if cash > 20% of portfolio
    CONCENTRATION_RISK_THRESHOLD: float = 30.0  # Flag if single asset > 30% of portfolio
    ANOMALY_ZSCORE_THRESHOLD: float = 2.5       # Statistical outlier cutoff
    LARGE_TX_THRESHOLD_USD: float = 25000.0     # Flag any single transaction >= $25k

    # System logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

config = Config()
