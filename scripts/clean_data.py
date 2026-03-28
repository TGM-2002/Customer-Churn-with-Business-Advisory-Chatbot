import pandas as pd

from config.settings import RAW_DATA_DIR,PROCESSED_DATA_DIR

CSV_PATH   = RAW_DATA_DIR /"Bank-Customer-Attrition-Insights-Data.csv"

df=pd.read_csv(CSV_PATH)



df.csv(PROCESSED_DATA_DIR / 'processed.csv')