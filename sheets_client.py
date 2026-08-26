"""
Wraps gspread so main.py can just call simple read/write functions.

Expected "Items" tab columns (row 1 = headers, exact names matter):
    Name | URL | Target Price | Current Price | Lowest Seen | Last Checked | Notes

Expected "History" tab columns:
    Timestamp | Name | URL | Price
"""
import json
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials

import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

ITEMS_HEADERS = ["Name", "URL", "Target Price", "Current Price", "Lowest Seen", "Last Checked", "Notes"]
HISTORY_HEADERS = ["Timestamp", "Name", "URL", "Price"]


def _client():
    info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def _open_sheet():
    gc = _client()
    return gc.open(config.SHEET_NAME)


def get_or_create_worksheets():
    sh = _open_sheet()

    try:
        items_ws = sh.worksheet(config.ITEMS_TAB)
    except gspread.WorksheetNotFound:
        items_ws = sh.add_worksheet(title=config.ITEMS_TAB, rows=200, cols=len(ITEMS_HEADERS))
        items_ws.append_row(ITEMS_HEADERS)

    try:
        history_ws = sh.worksheet(config.HISTORY_TAB)
    except gspread.WorksheetNotFound:
        history_ws = sh.add_worksheet(title=config.HISTORY_TAB, rows=1000, cols=len(HISTORY_HEADERS))
        history_ws.append_row(HISTORY_HEADERS)

    return items_ws, history_ws


def read_items(items_ws) -> list[dict]:
    """Returns a list of dicts, one per row, keyed by header name.
    Includes the 1-based sheet row number as "_row" for writing back later.
    """
    records = items_ws.get_all_records()
    rows = []
    for i, record in enumerate(records, start=2):  # row 1 is headers
        url = str(record.get("URL", "")).strip()
        if not url:
            continue  # skip blank rows
        record["_row"] = i
        rows.append(record)
    return rows


def update_item_price(items_ws, row: int, name: str | None, price: float | None, lowest_seen):
    """Writes Current Price, Lowest Seen, Last Checked (and Name, if we learned it) back to the row."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    updates = []
    if name:
        updates.append({"range": gspread.utils.rowcol_to_a1(row, ITEMS_HEADERS.index("Name") + 1), "values": [[name]]})
    if price is not None:
        updates.append({"range": gspread.utils.rowcol_to_a1(row, ITEMS_HEADERS.index("Current Price") + 1), "values": [[price]]})
        updates.append({"range": gspread.utils.rowcol_to_a1(row, ITEMS_HEADERS.index("Lowest Seen") + 1), "values": [[lowest_seen]]})
    updates.append({"range": gspread.utils.rowcol_to_a1(row, ITEMS_HEADERS.index("Last Checked") + 1), "values": [[now]]})

    if updates:
        items_ws.batch_update(updates)


def append_history(history_ws, name: str, url: str, price: float):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    history_ws.append_row([now, name, url, price])
