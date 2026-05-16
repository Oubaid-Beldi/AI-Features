"""
config.py
---------
Single source of truth for all environment variables and settings.
Import `settings` anywhere in the service; never read os.environ directly elsewhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "models/gemini-2.5-flash"     # fast + cheap; swap to gemini-1.5-pro if needed

    # Backend integration
    BACKEND_MODE: str = os.getenv("BACKEND_MODE", "mock")   # "mock" | "real"
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    # Service
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8001"))

    def is_mock(self) -> bool:
        return self.BACKEND_MODE.lower() == "mock"

    def validate(self) -> None:
        """Call at startup. Raises if critical config is missing."""
        if not self.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Copy .env.example to .env and add your key."
            )


settings = Settings()
