import os
import re
import csv
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

MIDDAY_URL = "https://www.lottery.net/michigan/daily-4-midday/numbers/2026"
EVENING_URL = "https://www.lottery.net/michigan/daily-4-evening/numbers/2026"

TZ = ZoneInfo("America/Detroit")

MONTH_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12
}


def _clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def parse_latest_result(url: str, draw_type: str) -> dict:
    """
    Returns dict:
      {
        'draw_type': 'MIDDAY'|'EVENING',
        'year': 2026,
        'month': 2,
        'day': 21,
        'day_name': 'Saturday',
        'number': '0577',  # string, leading zeros preserved
        'date_iso': '2026-02-21'
      }
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; daily4-bot/1.0)"
    }
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # For midday: ul.michigan.results.daily-4-midday
    # For evening: ul.michigan.results.daily-4-evening
    ul_class = "daily-4-midday" if draw_type.upper() == "MIDDAY" else "daily-4-evening"

    # Find the first row that contains the UL for this draw.
    # Pages are typically sorted newest -> older, so first match is latest.
    ul = soup.select_one(f"ul.michigan.results.{ul_class}")
    if not ul:
        raise RuntimeError(f"Could not find results list for {draw_type} at {url}")

    digits = "".join([_clean_spaces(li.get_text()) for li in ul.select("li")])
    if len(digits) != 4 or not digits.isdigit():
        raise RuntimeError(f"Unexpected number format for {draw_type}: '{digits}'")

    tr = ul.find_parent("tr")
    if not tr:
        raise RuntimeError(f"Could not find parent <tr> for {draw_type} result list")

    # The date/day is in the first <td><a> with a draw-specific href
    href_contains = "/daily-4-midday/numbers/" if draw_type.upper() == "MIDDAY" else "/daily-4-evening/numbers/"
    a = tr.select_one(f'td a[href*="{href_contains}"]')
    if not a:
        # Fallback: just grab the first td a
        a = tr.select_one("td a")

    raw = _clean_spaces(a.get_text() if a else "")
    # Example raw: "Saturday February 21, 2026"
    parts = raw.split(" ")
    if len(parts) < 4:
        raise RuntimeError(f"Unexpected date text for {draw_type}: '{raw}'")

    day_name = parts[0]
    month_name = parts[1]
    day = parts[2].replace(",", "")
    year = parts[3]

    if month_name not in MONTH_MAP:
        raise RuntimeError(f"Unknown month name '{month_name}' in '{raw}'")

    month = MONTH_MAP[month_name]
    day_i = int(day)
    year_i = int(year)

    date_iso = f"{year_i:04d}-{month:02d}-{day_i:02d}"

    return {
        "draw_type": draw_type.upper(),
        "year": year_i,
        "month": month,
        "day": day_i,
        "day_name": day_name,
        "number": digits,     # keep as TEXT
        "date_iso": date_iso
    }


def upsert_csv(csv_path: str, new_rows: list[dict]) -> tuple[int, int]:
    """
    Upsert by unique key: (date_iso, draw_type)
    Returns (added, updated)
    """
    fieldnames = ["date_iso", "year", "month", "day", "day_name", "draw_type", "number", "updated_at_local"]

    existing = {}
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            # If header differs, we still try to read what we can.
            for row in reader:
                d = row.get("date_iso") or ""
                t = (row.get("draw_type") or "").upper()
                if d and t:
                    existing[(d, t)] = row

    now_local = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %Z")

    added = 0
    updated = 0

    for r in new_rows:
        key = (r["date_iso"], r["draw_type"])
        out = {
            "date_iso": r["date_iso"],
            "year": str(r["year"]),
            "month": str(r["month"]),
            "day": str(r["day"]),
            "day_name": r["day_name"],
            "draw_type": r["draw_type"],
            # store number as text; Excel users can format as text. (Leading zeros preserved in CSV content.)
            "number": r["number"],
            "updated_at_local": now_local
        }

        if key in existing:
            # update if different number (or overwrite anyway)
            if existing[key].get("number") != out["number"]:
                existing[key] = out
                updated += 1
        else:
            existing[key] = out
            added += 1

    # Write back sorted by date then draw_type (MIDDAY then EVENING)
    def sort_key(item):
        (date_iso, draw_type) = item[0]
        # ensure midday comes first
        draw_rank = 0 if draw_type == "MIDDAY" else 1
        return (date_iso, draw_rank)

    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for _, row in sorted(existing.items(), key=sort_key):
            writer.writerow(row)

    return added, updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
       "--csv",
    default="D:/prediction-algo/daily-4-update/main-data-set-daily-4.csv",
    help="Path to CSV to update"
        )
    args = ap.parse_args()

    midday = parse_latest_result(MIDDAY_URL, "MIDDAY")
    evening = parse_latest_result(EVENING_URL, "EVENING")

    added, updated = upsert_csv(args.csv, [midday, evening])

    print("Latest Midday:", midday)
    print("Latest Evening:", evening)
    print(f"CSV updated: added={added}, updated={updated}")
    print("CSV path:", os.path.abspath(args.csv))


if __name__ == "__main__":
    main()