import csv
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

START_DATE = date(2020, 1, 1)
END_DATE = date.today()  # run-time "today" on your machine

MIDDAY_YEAR_URL = "https://www.lottery.net/michigan/daily-4-midday/numbers/{year}"
EVENING_YEAR_URL = "https://www.lottery.net/michigan/daily-4-evening/numbers/{year}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

DATE_RE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})$")

def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=40)
    r.raise_for_status()
    return r.text

def parse_year_page(html: str) -> List[Tuple[date, str]]:
    """
    Returns list of (draw_date, number_string "####") from a Lottery.net year page.
    The page shows:
      DayOfWeek Month Day, Year
      * digit
      * digit
      * digit
      * digit
    """
    soup = BeautifulSoup(html, "html.parser")
    text_lines = [ln.strip() for ln in soup.get_text("\n").splitlines() if ln.strip()]

    results: List[Tuple[date, str]] = []
    i = 0
    while i < len(text_lines):
        m = DATE_RE.match(text_lines[i])
        if not m:
            i += 1
            continue

        month_name = m.group(2)
        day_num = int(m.group(3))
        year_num = int(m.group(4))
        if month_name not in MONTHS:
            i += 1
            continue

        d = date(year_num, MONTHS[month_name], day_num)

        # Look ahead for 4 single-digit lines (sometimes appear with bullets, but text extraction leaves digits)
        digits: List[str] = []
        j = i + 1
        while j < len(text_lines) and len(digits) < 4:
            if re.fullmatch(r"\d", text_lines[j]):
                digits.append(text_lines[j])
            j += 1

        if len(digits) == 4:
            results.append((d, "".join(digits)))
            i = j
        else:
            i += 1

    return results

def collect_game(draw_type: str, url_template: str) -> Dict[date, str]:
    """
    draw_type is 'midday' or 'evening'
    Returns dict {date: "####"} for 2020..END_DATE.year
    """
    out: Dict[date, str] = {}
    for year in range(START_DATE.year, END_DATE.year + 1):
        url = url_template.format(year=year)
        html = fetch(url)
        rows = parse_year_page(html)
        for d, num in rows:
            if START_DATE <= d <= END_DATE:
                out[d] = num
        print(f"Parsed {draw_type} {year}: {len(rows)} entries")
    return out

def main():
    midday = collect_game("midday", MIDDAY_YEAR_URL)
    evening = collect_game("evening", EVENING_YEAR_URL)

    # Union of all dates in range
    all_dates = sorted(set(midday.keys()) | set(evening.keys()))

    out_file = "michigan_daily4_2020_to_today.csv"
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "midday", "evening"])
        for d in all_dates:
            w.writerow([d.isoformat(), midday.get(d, ""), evening.get(d, "")])

    print(f"\n✅ Saved: {out_file}")
    print(f"✅ Rows: {len(all_dates)}")
    print(f"Date range: {START_DATE.isoformat()} → {END_DATE.isoformat()}")

if __name__ == "__main__":
    main()
