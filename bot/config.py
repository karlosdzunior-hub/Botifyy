import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROK_API_KEY = os.getenv("GROK_API_KEY", "")

WELCOME_CREDITS = 150
REFERRAL_BONUS = 50

BOT_COSTS = {
    "simple": 150,
    "medium": 300,
    "complex": 600,
    "miniapp_simple": 400,
    "miniapp_complex": 800,
    "update": 100,
}

HOSTING_PLANS = {
    "mini": {"price_rub": 399, "bots": 1, "users": 2000, "name": "Мини"},
    "standard": {"price_rub": 890, "bots": 3, "users": 20000, "name": "Стандарт"},
    "max": {"price_rub": 1990, "bots": 10, "users": None, "name": "Макс"},
}

GROQ_MODELS = [
    "qwen-qwq-32b",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
]

DB_PATH = "/home/runner/workspace/botify.db"
