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

for dir in [CONFIG_DIR,DATABASE_DIR,SCRIPTS_DIR,DATA_DIR,RAW_DATA_DIR,PROCESSED_DATA_DIR,MODELS_DIR,SRC_DIR]:
    dir.mkdir(parents=True,exist_ok=True)
    
    
# =============================================================
# DATABASE SET UP
# =============================================================
DB_NAME=os.getenv("DB_NAME")
DB_DRIVER=os.getenv("DB_DRIVER")
DB_HOST=os.getenv("DB_HOST")
DB_USER=os.getenv("DB_USER")
DB_PASSWORD=os.getenv("DB_PASSWORD")
DATABASE_URL=os.getenv("DATABASE_URL")

DB_POOL_SIZE = os.getenv("DB_POOL_SIZE")
DB_MAX_OVERFLOW = os.getenv("DB_MAX_OVERFLOW ")
DB_ECHO = os.getenv("DB_ECHO")

