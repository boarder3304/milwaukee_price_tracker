"""
Sends deal-alert emails via Gmail SMTP.

Requires a Gmail "App Password" (not your regular password) - generate one at
https://myaccount.google.com/apppasswords with 2FA enabled on the account.
"""
import smtplib
from email.mime.text import MIMEText

import config


def send_deal_alert(deals: list[dict]):
    """deals: list of {"name": str, "url": str, "price": float, "target": float, "lowest_seen": float}"""
    if not deals:
        return

    subject = f"🔧 {len(deals)} Milwaukee/Packout deal{'s' if len(deals) != 1 else ''} hit your target price"

    lines = []
    for d in deals:
        lines.append(
            f"{d['name']}\n"
            f"  Price: ${d['price']:.2f}  (your target: ${d['target']:.2f}, lowest ever seen: ${d['lowest_seen']:.2f})\n"
            f"  {d['url']}\n"
        )
    body = "\n".join(lines)

    _send(subject, body)


def send_error_summary(errors: list[dict]):
    """Optional: notify when items fail to fetch, so broken scrapers don't fail silently forever."""
    if not errors:
        return

    subject = f"⚠️ Packout tracker: {len(errors)} item(s) failed to check"
    lines = [f"{e['name'] or e['url']}\n  {e['error']}\n" for e in errors]
    body = "\n".join(lines)
    _send(subject, body)


def _send(subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_ADDRESS
    msg["To"] = config.NOTIFY_EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_ADDRESS, [config.NOTIFY_EMAIL_TO], msg.as_string())
