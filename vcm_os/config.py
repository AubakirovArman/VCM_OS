import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("VCM_DATA_DIR", str(PROJECT_ROOT / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "vcm_os.db"
EVENT_LOG_DIR = DATA_DIR / "events"
EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = os.getenv("VCM_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DEVICE = os.getenv("VCM_EMBEDDING_DEVICE", "cuda:3")
EMBEDDING_BATCH_SIZE = int(os.getenv("VCM_EMBEDDING_BATCH_SIZE", "32"))

DEFAULT_TOKEN_BUDGET = int(os.getenv("VCM_DEFAULT_TOKEN_BUDGET", "32768"))
MAX_VECTOR_RESULTS = int(os.getenv("VCM_MAX_VECTOR_RESULTS", "50"))
MAX_SPARSE_RESULTS = int(os.getenv("VCM_MAX_SPARSE_RESULTS", "50"))

SESSION_RESTORE_DAYS_THRESHOLD = int(os.getenv("VCM_SESSION_RESTORE_DAYS", "7"))
