import csv
import re
import requests
from bs4 import BeautifulSoup

URL = "https://www.lottery.net/michigan/daily-4-midday/numbers/2025"
OUT = "mi_daily4_midday_2025.csv"

# Matches: "Wednesday December 31, 2025"
DATE_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(\d{1,2}),\s+(2025)$"
)

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.lottery.net/"
}

def main():
    r = requests.get(URL, headers=HEADERS, timeout=40)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    lines = [ln.strip() for ln in soup.get_text("\n").splitlines() if ln.strip()]

    rows = []
    i = 0
    while i < len(lines):
        m = DATE_RE.match(lines[i])
        if not m:
            i += 1
            continue

        month_name = m.group(2)
        day_num = int(m.group(3))
        year_num = int(m.group(4))
        month_num = MONTHS[month_name]

        # Next 4 single-digit lines are the winning number digits
        digits = []
        j = i + 1
        while j < len(lines) and len(digits) < 4:
            if re.fullmatch(r"\d", lines[j]):
                digits.append(lines[j])
            j += 1

        if len(digits) == 4:
            date_iso = f"{year_num:04d}-{month_num:02d}-{day_num:02d}"
            number = "".join(digits)
            rows.append((date_iso, number))
            i = j
        else:
            i += 1

    # Write CSV
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "midday"])
        w.writerows(rows)

    print(f"✅ Saved {len(rows)} rows to {OUT}")

if __name__ == "__main__":
    main()
