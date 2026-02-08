import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dataclasses import dataclass
from typing import Optional


def _require(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v


@dataclass(frozen=True)
class Settings:
    sheet_name: str
    google_service_account_json: dict
    openai_api_key: Optional[str]
    cors_allow_origins: list[str]


def load_settings() -> Settings:
    sheet_name = os.getenv("SHEET_NAME", "Task_Manager")

    sa_raw = _require("GOOGLE_SERVICE_ACCOUNT_JSON")
    try:
        google_service_account_json = json.loads(sa_raw)
    except json.JSONDecodeError as e:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON must be valid JSON") from e

    openai_api_key = os.getenv("OPENAI_API_KEY")

    cors_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
    origins = [o.strip() for o in cors_allow_origins.split(",")] if cors_allow_origins else ["*"]

    return Settings(
        sheet_name=sheet_name,
        google_service_account_json=google_service_account_json,
        openai_api_key=openai_api_key,
        cors_allow_origins=origins,
    )
