import os
from dotenv import load_dotenv

load_dotenv()


# ──────────────────────────────────────────────────────────
# API Keys
# ──────────────────────────────────────────────────────────

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
UPSTAGE_API_KEY: str = os.getenv("UPSTAGE_API_KEY", "")
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY", "")


# ──────────────────────────────────────────────────────────
# LLM Model Names
# ──────────────────────────────────────────────────────────

GPT_MODEL: str = "gpt-4o"
GEMINI_VISION_MODEL: str = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL: str = "gemini-2.5-flash-lite"


# ──────────────────────────────────────────────────────────
# Upstage API Endpoints
# ──────────────────────────────────────────────────────────

UPSTAGE_LAYOUT_ANALYSIS_URL: str = "https://api.upstage.ai/v1/document-ai/layout-analysis"


# ──────────────────────────────────────────────────────────
# Log Paths
# ──────────────────────────────────────────────────────────

LOG_DIR: str = "logs"
EVALUATION_LOG_FILE: str = f"{LOG_DIR}/evaluation_history.jsonl"
