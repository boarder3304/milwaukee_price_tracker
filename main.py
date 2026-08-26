"""
Entry point - run this on a schedule (see .github/workflows/check_prices.yml).

For each row in the "Items" tab of the Google Sheet:
  1. Fetch the current price from the right retailer
  2. Update Current Price / Lowest Seen / Last Checked in the sheet
  3. Append a row to the History tab
  4. If price <= Target Price, queue a deal alert email

Errors on individual items don't stop the run - they're collected and
optionally emailed as a summary so silent scraper breakage doesn't go
unnoticed for months.
"""
from retailers import fetch_price
from sheets_client import get_or_create_worksheets, read_items, update_item_price, append_history
from notifier import send_deal_alert, send_error_summary


def _to_float(value) -> float | None:
    if value in (None, "", "N/A"):
        return None
    try:
        return float(str(value).replace("$", "").replace(",", ""))
    except ValueError:
        return None


def main():
    items_ws, history_ws = get_or_create_worksheets()
    items = read_items(items_ws)

    if not items:
        print("No items found in the sheet yet - add rows with at least a URL.")
        return

    deals = []
    errors = []

    for item in items:
        url = item["URL"].strip()
        sheet_name = (item.get("Name") or "").strip() or None
        target_price = _to_float(item.get("Target Price"))
        prior_lowest = _to_float(item.get("Lowest Seen"))

        result = fetch_price(url)
        price = result["price"]
        fetched_name = result["name"]
        display_name = sheet_name or fetched_name or url

        if result["error"]:
            print(f"[ERROR] {display_name}: {result['error']}")
            errors.append({"name": display_name, "url": url, "error": result["error"]})
            # Still bump Last Checked so it's obvious in the sheet this ran
            update_item_price(items_ws, item["_row"], fetched_name, None, prior_lowest)
            continue

        lowest_seen = price if prior_lowest is None else min(prior_lowest, price)

        print(f"[OK] {display_name}: ${price:.2f} (target ${target_price if target_price else 'none'})")

        update_item_price(items_ws, item["_row"], fetched_name, price, lowest_seen)
        append_history(history_ws, display_name, url, price)

        if target_price is not None and price <= target_price:
            deals.append({
                "name": display_name,
                "url": url,
                "price": price,
                "target": target_price,
                "lowest_seen": lowest_seen,
            })

    if deals:
        send_deal_alert(deals)
        print(f"Sent deal alert for {len(deals)} item(s).")

    if errors:
        send_error_summary(errors)


if __name__ == "__main__":
    main()
