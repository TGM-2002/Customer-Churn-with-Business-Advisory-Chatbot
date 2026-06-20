import os 
from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

BASE_DIR=Path(__file__).resolve().parent.parent
CONFIG_DIR=BASE_DIR / 'config'
DATABASE_DIR=BASE_DIR /'database'
SCRIPTS_DIR=BASE_DIR / 'scripts'
DATA_DIR=BASE_DIR / 'data'
RAW_DATA_DIR=DATA_DIR /'raw'
PROCESSED_DATA_DIR=DATA_DIR /'processed'
MODELS_DIR=BASE_DIR / ' models'
SRC_DIR=BASE_DIR / 'src'
RAW_DATASET_DIR=RAW_DATA_DIR/ 'Bank-Customer-Attrition-Insights-Data.csv'

# =============================================================
# DATABASE SET UP
# =============================================================
DB_NAME=os.getenv("DB_NAME")
DB_DRIVER=os.getenv("DB_DRIVER")
DB_HOST=os.getenv("DB_HOST")
DB_USER=os.getenv("DB_USER")
DB_PASSWORD=os.getenv("DB_PASSWORD")
DATABASE_URL=os.getenv("DATABASE_URL")


DB_POOL_SIZE    = int(os.getenv("DB_POOL_SIZE", 5))       # cast to int
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 10))   # cast to int
DB_ECHO         = os.getenv("DB_ECHO", "false").lower() == "true"  # cast to bool


# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

# Model types available
AVAILABLE_CLASSIFIERS = [
    'logistic_regression',
    'naive_bayes',
    'svm',
    'random_forest'
]
# Model versioning
MODEL_VERSION = os.getenv('MODEL_VERSION', 'v1.0.0')

# Default classifier
DEFAULT_CLASSIFIER = os.getenv('DEFAULT_CLASSIFIER', 'xgboost')

# Training parameters
TEST_SIZE = float(os.getenv('TEST_SIZE', '0.2'))
RANDOM_STATE = int(os.getenv('RANDOM_STATE', '42'))
CV_FOLDS = int(os.getenv('CV_FOLDS', '5'))

for dir in [CONFIG_DIR,DATABASE_DIR,SCRIPTS_DIR,DATA_DIR,RAW_DATA_DIR,PROCESSED_DATA_DIR,MODELS_DIR,SRC_DIR]:
    dir.mkdir(parents=True,exist_ok=True)
    
    

# ============================================================================
# HUGGING FACE / LLM CONFIGURATION
# ============================================================================

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")


# ============================================================================
# CHROMADB / RAG CONFIGURATION
# ============================================================================

CHROMADB_PATH    = DATA_DIR / "chroma_db"
COLLECTION_NAME  = os.getenv("COLLECTION_NAME", "banking_strategy")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

STRATEGY_DOCS_DIR = DATA_DIR / "strategy_documents"


# ============================================================================
# FEATURE EXCLUSIONS (used when reconstructing the model's feature row)
# ============================================================================

COLUMNS_TO_EXCLUDE = [
    "customer_id", "surname", "churn_probability",
    "churn_risk_band", "top_churn_driver",
]


for dir in [CONFIG_DIR, DATABASE_DIR, SCRIPTS_DIR, DATA_DIR, RAW_DATA_DIR,
            PROCESSED_DATA_DIR, MODELS_DIR, SRC_DIR, CHROMADB_PATH, STRATEGY_DOCS_DIR]:
    dir.mkdir(parents=True, exist_ok=True)