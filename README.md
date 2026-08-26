# Packout / Milwaukee Price Tracker

A personal deal-watcher: keep a wishlist in a Google Sheet, and get an email
when something drops to (or below) the price you set. Runs for free once a
day via GitHub Actions - no server to maintain.

## How it works

1. You list items in a Google Sheet (URL + your target price).
2. A GitHub Actions job runs daily, checks each item's current price.
3. If the price is at or under your target, you get an email.
4. Every check is logged to a "History" tab, so you can see price trends over time.

Supported retailers: Amazon (via Keepa API), Home Depot, Milwaukee Tool's own
site, Ace Hardware, and a generic fallback for anything else.

**Note on reliability:** Home Depot and Ace Hardware don't publish official
APIs, so this reads their page's product data directly. That's inherently a
bit fragile - if a retailer changes their site, that scraper may need a fix.
The script is built so one broken item doesn't stop the others from being
checked, and you'll get an email if something errors out repeatedly.

---

## Setup

### 1. Create the Google Sheet

Create a new Google Sheet named exactly `Packout Price Tracker` (or pick your
own name and set `SHEET_NAME` accordingly later). The script will
auto-create the `Items` and `History` tabs with headers the first time it
runs, but you can also create the `Items` tab yourself with these columns:

| Name | URL | Target Price | Current Price | Lowest Seen | Last Checked | Notes |
|------|-----|---------------|----------------|--------------|----------------|-------|

- **URL** is the only required field - paste a product page link.
- **Name** is optional; the script will try to fill it in automatically from the page.
- **Target Price** is optional - leave blank to just track price history without alerts.

To add or remove items later, just edit rows in this sheet.

### 2. Create a Google Cloud service account (so the script can edit your sheet)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/), create a project (or use an existing one).
2. Enable the **Google Sheets API** for that project.
3. Go to **APIs & Services > Credentials > Create Credentials > Service Account**.
4. Once created, open the service account, go to **Keys > Add Key > Create new key > JSON**. This downloads a `.json` file - keep it private, it's a credential.
5. Open your Google Sheet, click **Share**, and share it with the service account's email address (looks like `something@your-project.iam.gserviceaccount.com`), giving it **Editor** access.

### 3. Create a Gmail App Password (so the script can send you email)

1. Turn on 2-Step Verification on the Gmail account you want to send from, if not already on.
2. Go to <https://myaccount.google.com/apppasswords> and create an app password.
3. Save the 16-character password it gives you - you'll use it as `GMAIL_APP_PASSWORD`.

### 4. (Optional) Get a Keepa API key for Amazon tracking

Amazon blocks plain scraping, so Amazon price checks use the
[Keepa API](https://keepa.com/#!api) instead. Sign up and grab an API key.
This costs a small monthly fee depending on request volume, but for a short
wishlist checked once a day it should stay in Keepa's cheapest tier. If you
skip this, Amazon items will just show an error in the run log rather than
breaking the rest of the check - HD/Milwaukee/Ace items are unaffected.

### 5. Push this project to a GitHub repo

Create a new repo (can be private) and push all these files to it.

### 6. Add GitHub Actions secrets

In your repo: **Settings > Secrets and variables > Actions > New repository secret**. Add:

| Secret name | Value |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | The *entire contents* of the JSON key file from step 2 |
| `SHEET_NAME` | `Packout Price Tracker` (or whatever you named it) |
| `GMAIL_ADDRESS` | The Gmail address you're sending from |
| `GMAIL_APP_PASSWORD` | The app password from step 3 |
| `NOTIFY_EMAIL_TO` | Where you want alerts sent (can be the same Gmail address) |
| `KEEPA_API_KEY` | (Optional) your Keepa API key, if using Amazon tracking |

### 7. Test it

Go to the **Actions** tab in your repo, select "Check Packout/Milwaukee
Prices", and click **Run workflow** to trigger it manually. Check the run
log for errors, and check your sheet to confirm prices got filled in.

By default it then runs automatically once a day (13:00 UTC) - edit the
`cron` line in `.github/workflows/check_prices.yml` to change the schedule.

---

## Running locally (optional, for testing/debugging)

```bash
pip install -r requirements.txt

export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat path/to/your-key.json)"
export SHEET_NAME="Packout Price Tracker"
export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="your16charapppassword"
export NOTIFY_EMAIL_TO="you@gmail.com"
export KEEPA_API_KEY="optional"

python main.py
```

## Extending

- **Adjust the schedule:** edit the `cron` line in the workflow file.
- **Add a new retailer:** add a new file in `retailers/`, following the
  pattern in `retailers/milwaukeetool.py`, then register it in
  `retailers/__init__.py`'s `get_fetcher()`.
- **Change alert logic:** it's all in `main.py` - e.g. you could alert on
  "any drop" instead of "at/below target" by comparing to `Lowest Seen`
  instead of `Target Price`.
