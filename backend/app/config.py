"""
Application Configuration using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SPLITFLOW_SECRET_KEY: str = "splitflow_default_dev_secret_key_change_in_prod_32"
    ENVIRONMENT: str = "sandbox"
    DATABASE_URL: str = "sqlite:///./splitflow.db"
    
    # PayPal Sandbox Configuration
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_API_BASE: str = "https://api-m.sandbox.paypal.com"
    PAYPAL_WEBHOOK_ID: Optional[str] = None
    
    # AI Engine
    GEMINI_API_KEY: Optional[str] = None

    model_config = {
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()
