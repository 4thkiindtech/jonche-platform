"""
packages/config/settings.py
Shared configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base config — shared across all apps."""
    SECRET_KEY: str      = os.getenv("SECRET_KEY", "dev-secret-key")
    FLASK_ENV: str       = os.getenv("FLASK_ENV", "development")
    DATABASE_URL: str    = os.getenv("DATABASE_URL", "sqlite:///jonche.db")
    API_KEY: str         = os.getenv("API_KEY", "dev-api-key")

    # App ports
    WEB_PORT: int        = int(os.getenv("WEB_PORT", 5000))
    API_PORT: int        = int(os.getenv("API_PORT", 5001))

    # Apliiq print-on-demand / fulfillment
    APLIIQ_APP_KEY: str      = os.getenv("APLIIQ_APP_KEY", "")
    APLIIQ_SHARED_SECRET: str = os.getenv("APLIIQ_SHARED_SECRET", "")

    @property
    def is_dev(self) -> bool:
        return self.FLASK_ENV == "development"

    @property
    def is_prod(self) -> bool:
        return self.FLASK_ENV == "production"


class DropConfig:
    """Business rules for drops."""
    MAX_UNITS_PER_DROP: int        = 500
    MIN_PRICE: int                 = 100
    HYPE_THRESHOLD_HIGH: int       = 80   # % sold to be considered "high hype"
    SCARCITY_THRESHOLD: int        = 150  # max units to qualify as "limited"


class MemberConfig:
    """VIP tier thresholds (lifetime spend in USD)."""
    GOLD_THRESHOLD: int   = 8_000
    SILVER_THRESHOLD: int = 2_500
    BRONZE_THRESHOLD: int = 0


class RetailerConfig:
    """Retailer tier allocations."""
    PREMIER_MAX_ALLOCATION: int = 50
    SELECT_MAX_ALLOCATION: int  = 20
    BASIC_MAX_ALLOCATION: int   = 10


settings = Config()
