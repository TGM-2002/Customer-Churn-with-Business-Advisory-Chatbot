# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ChurnWatch** — a customer churn prediction and AI-powered retention advisory platform for retail banking. It combines PostgreSQL, multi-classifier ML (Random Forest, Logistic Regression, Gradient Boosting), SHAP explainability, ChromaDB RAG, and a Qwen LLM to generate per-customer retention memos, surfaced through a Streamlit frontend.

## Environment & Setup

**Python version**: 3.13 (managed via `.python-version`)

**Dependency management**: `uv` with a lock file — prefer `uv sync` over `pip install`.

```bash
uv sync                          # install from lock file
# OR
pip install -r requirements.txt
```

**Required local service**: PostgreSQL on `localhost:5432`
- Database: `customer_churn`
- User/password: `trinity` / `trinity`
- Tables are auto-created via SQLAlchemy `Base.metadata.create_all()` on first DB connection.

**Environment variables** are in `.env` (already committed, not in `.gitignore`):
- `TARGET_DATABASE_URL` — local PostgreSQL connection string
- `SOURCE_DATABASE_URL` — cloud Neon DB (for migration only)
- `HF_TOKEN` / `HF_MODEL` — Hugging Face inference (Qwen/Qwen2.5-72B-Instruct)

## Common Commands

```bash
# Seed database from raw CSV (includes USD→ZAR conversion)
python scripts/insert_into_db.py

# Train all classifiers and save the best model
python scripts/train_model.py

# Train a specific classifier
python scripts/train_model.py --model random_forest   # or logistic_regression / gradient_boosting

# Evaluate the saved model on the held-out test set
python src/classifier/evaluate.py

# Run the Streamlit frontend
cd frontend && streamlit run Home.py

# Migrate schema + data from cloud DB to local
python database/migrate_db.py
```

## Architecture

### Data flow

```
CSV (data/raw/)
  → scripts/insert_into_db.py   (ETL + USD→ZAR + derived features)
  → PostgreSQL (6 tables)
  → scripts/train_model.py      (join all tables → train/val/test split)
  → models/ (.joblib artifacts)
  → src/ai_advisor/             (SHAP context + RAG + LLM)
  → frontend/                   (Streamlit pages)
```

### Database schema (`database/schemas.py`)

Six SQLAlchemy ORM tables, all keyed on `customer_id` (UUID):

| Table | Role |
|---|---|
| `customers` | Core profile + derived segment/lifecycle/age_band |
| `product_holdings` | Accounts, balances, product diversity |
| `support_interactions` | Complaints, satisfaction scores |
| `behavioral_signals` | Points, activity, engagement |
| `churn_scores` | ML output: probability, risk_band, SHAP driver, model_version |

Enums encode business logic: `CustomerSegment` (Affluent/Mid/Mass), `ChurnRiskBand` (Low/Medium/High/Critical), South African `GeographyEnum` (provinces), etc. Derived columns (e.g. `activity_drop_flag`, `is_high_risk_support`) are computed at insert time in `scripts/insert_into_db.py`, not in the DB.

### ML pipeline (`src/classifier/models.py`, `scripts/train_model.py`)

- `Churn_Classifier` wraps all three models behind a common `.fit()` / `.predict()` / `.predict_proba()` interface.
- Training uses an 80/10/10 stratified split (train/val/test). Scaler and `LabelEncoder`s are fit **on train only** to avoid data leakage.
- Model selection: race all three on the validation set, save the winner plus metadata to `.joblib` via `save_model()`.
- Serialized artifact contains: model, scaler, label_encoders, feature_names, metadata dict.

### AI Advisory layer (`src/ai_advisor/`)

- **`advisor.py`** (`ChurnAdvisor`) — takes a `customer_id`, builds context, retrieves RAG chunks, calls HF inference API, returns an 8-section retention memo.
- **`context_builder.py`** (`CustomerContextBuilder`) — fetches all 5 joined tables, reconstructs the feature vector, runs SHAP to produce top-6 drivers per customer.
- **`rag/document_store.py`** (`RAGDocumentStore`) — ChromaDB collection at `data/chroma_db/`, embeddings via `all-MiniLM-L6-v2`, ingest PDFs/TXT/MD from `data/strategy_documents/` and `data/financial_docs/`.

### Frontend (`frontend/`)

Streamlit multi-page app launched from `frontend/Home.py`:

| Page | File | Purpose |
|---|---|---|
| Home | `Home.py` | Landing / navigation cards |
| Dashboard | `pages/1_Dashboard.py` | SOM heatmaps, KPIs, portfolio snapshot |
| Customers | `pages/2_Customers.py` | Search/filter by risk band, customer detail cards |
| AI Advisory | `pages/3_AI_Advisory.py` | Per-customer LLM retention memo + SHAP chart |

Shared helpers in `frontend/utils/helpers.py`: CSS injection, sidebar render, color maps (`RISK_COLORS`, `SEG_COLORS`), and a small `RAW_CUSTOMERS` mock dataset used when the DB is unavailable.

### SOM pipeline (`src/som/`)

`som_core.py` trains an 8×8 MiniSom grid on the joined feature DataFrame, outputs U-matrix, churn heatmap, and 3D scatter to `data/processed/`. `som_visualisation.py` provides standalone plotting functions for those artefacts.

### Configuration (`config/settings.py`)

Single source of truth for all paths, DB pool settings, model hyperparameter defaults, feature exclusion lists (`COLUMNS_TO_EXCLUDE`), and LLM config. Import from here rather than hard-coding paths or env vars elsewhere.
