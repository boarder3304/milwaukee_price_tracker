"""
Configuration loaded from environment variables (set as GitHub Actions secrets
when running in CI, or in a local .env file when testing locally).
"""
import os

# Google Sheets
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
SHEET_NAME = os.environ.get("SHEET_NAME", "Milwaukee Price Tracker")
ITEMS_TAB = os.environ.get("ITEMS_TAB", "Items")
HISTORY_TAB = os.environ.get("HISTORY_TAB", "History")

# Email (Gmail SMTP with an App Password - not your normal password)
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
NOTIFY_EMAIL_TO = os.environ.get("NOTIFY_EMAIL_TO", "")

# Optional: Keepa API key for Amazon price history (https://keepa.com/#!api)
#KEEPA_API_KEY = os.environ.get("KEEPA_API_KEY", "")

# Request behavior
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
