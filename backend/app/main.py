"""
SplitFlow AI — Backend Application Entry Point.
Initializes FastAPI, registers routers, sets up SQLite WAL & balance triggers,
and seeds sandbox accounts for local testing and demo delivery.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.services.ledger_service import init_ledger_schema_and_triggers
from app.models import Creator, Collaborator, UserSession
from app.routers import auth, contracts, webhooks, payouts, ledger, copilot
from datetime import datetime, timedelta, timezone

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create database tables
    Base.metadata.create_all(bind=engine)

    # 2. Initialize Chart of Accounts and SQLite balance enforcement triggers
    db = SessionLocal()
    try:
        init_ledger_schema_and_triggers(db)

        # 3. Seed Demo Creator & Collaborators if database is empty
        creator = db.query(Creator).filter_by(email="creator-biz@sandbox.com").first()
        if not creator:
            creator = Creator(
                business_name="Apex Media Studios (Creator)",
                email="creator-biz@sandbox.com",
                paypal_merchant_id="MERCHANT-SANDBOX-101"
            )
            db.add(creator)
            db.flush()

            # Seed Demo Session Token for instant demo access
            demo_session = UserSession(
                id="demo_session_token_12345",
                creator_id=creator.id,
                role="CREATOR_OWNER",
                expires_at=datetime.now(timezone.utc) + timedelta(days=365)
            )
            db.add(demo_session)

            # Seed Pre-Verified Collaborators
            collabs = [
                Collaborator(
                    creator_id=creator.id,
                    full_name="Mark Santos (Video Editor)",
                    role="Video Editor",
                    verified_paypal_email="editor-ph@sandbox.com",
                    default_currency="USD"
                ),
                Collaborator(
                    creator_id=creator.id,
                    full_name="Ana Silva (Thumbnail Designer)",
                    role="Thumbnail Designer",
                    verified_paypal_email="designer-br@sandbox.com",
                    default_currency="USD"
                ),
                Collaborator(
                    creator_id=creator.id,
                    full_name="David Miller (Talent Manager)",
                    role="Talent Manager",
                    verified_paypal_email="manager-us@sandbox.com",
                    default_currency="USD"
                )
            ]
            db.add_all(collabs)
            db.commit()
    finally:
        db.close()

    yield

app = FastAPI(
    title="SplitFlow AI API",
    description="Production-grade AI-assisted contract parsing, invoicing, and payout execution engine with PayPal.",
    version="3.3.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(webhooks.router)
app.include_router(payouts.router)
app.include_router(ledger.router)
app.include_router(copilot.router)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
assets_dir = os.path.join(static_dir, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
@app.get("/dashboard")
def serve_dashboard():
    static_file = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return {
        "status": "online",
        "service": "SplitFlow AI Engine",
        "version": "3.3.0",
        "paypal_environment": "sandbox"
    }

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "SplitFlow AI Engine",
        "version": "3.3.0",
        "paypal_environment": "sandbox"
    }
