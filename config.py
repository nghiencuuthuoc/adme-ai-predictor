from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional during bootstrap
    def load_dotenv() -> bool:
        return False

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "ADME-AI Predictor")
    adme_api_url: str = os.getenv("ADME_API_URL", "")
    adme_api_key: str = os.getenv("ADME_API_KEY", "")
    request_timeout: int = int(os.getenv("ADME_API_TIMEOUT", "20"))
    history_path: Path = Path(os.getenv("ADME_HISTORY_PATH", ".adme_history.json"))
    max_history_items: int = int(os.getenv("ADME_MAX_HISTORY_ITEMS", "20"))


settings = Settings()
