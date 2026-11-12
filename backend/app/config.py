"""
Application Configuration using Pydantic Settings.
Loads environment variables from root .env or backend/.env.
Normalizes aliases and filters out placeholder strings.
"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

class Settings(BaseSettings):
    # App Security
    SPLITFLOW_SECRET_KEY: str = Field(
        default="splitflow_default_dev_secret_key_change_in_prod_32",
        validation_alias="SPLITFLOW_CREATOR_SECRET"
    )
    ENVIRONMENT: str = "sandbox"
    DATABASE_URL: str = "sqlite:///./splitflow.db"
    
    # PayPal Sandbox Configuration
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_API_BASE: str = Field(
        default="https://api-m.sandbox.paypal.com",
        validation_alias="PAYPAL_API_BASE_URL"
    )
    PAYPAL_WEBHOOK_ID: Optional[str] = None

    # Payout Safety Limits
    MAX_BATCH_LIMIT_CENTS: int = 500000
    PAYOUT_CURRENCY: str = "USD"

    # Application URLs
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # AI Engine
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None

    @field_validator("PAYPAL_WEBHOOK_ID", "GEMINI_API_KEY", "LLM_MODEL", mode="before")
    @classmethod
    def clean_placeholders(cls, v):
        if isinstance(v, str) and (v.startswith("paste_") or v.startswith("check_") or v.startswith("your_")):
            return None
        return v

    @field_validator("SPLITFLOW_SECRET_KEY", mode="before")
    @classmethod
    def clean_secret_key(cls, v):
        if isinstance(v, str) and v.startswith("paste_"):
            return "splitflow_default_dev_secret_key_change_in_prod_32"
        return v or "splitflow_default_dev_secret_key_change_in_prod_32"

    model_config = {
        "env_file": (
            os.path.join(ROOT_DIR, ".env"),
            os.path.join(BASE_DIR, "..", ".env"),
            ".env"
        ),
        "extra": "ignore"
    }

settings = Settings()
