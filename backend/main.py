from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import customers, dashboard, advisory

app = FastAPI(
    title="ChurnWatch API",
    description="Customer churn prediction and AI-powered retention advisory API for ChurnWatch.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit dev origin; widen for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers.router, prefix="/api/v1/customers", tags=["Customers"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(advisory.router, prefix="/api/v1/advisory", tags=["Advisory"])


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
