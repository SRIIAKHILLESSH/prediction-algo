import csv
import re
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError

URL = "https://www.lottery.net/michigan/daily-4-midday/numbers/2025"
OUT = "mi_daily4_midday_2025.csv"

DATE_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(\d{1,2}),\s+(2025)$"
)

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
        page = await context.new_page()

        # ✅ Use domcontentloaded instead of networkidle
        await page.goto(URL, wait_until="domcontentloaded", timeout=120000)

        # ✅ Wait for something that should exist on the page
        # If this fails, we still try to parse the HTML we have.
        try:
            await page.wait_for_timeout(3000)  # give it 3 seconds to render
        except PWTimeoutError:
            pass

        html = await page.content()
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
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

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "midday"])
        w.writerows(rows)

    print(f"✅ Saved {len(rows)} rows to {OUT}")

    # Debug if nothing extracted
    if len(rows) == 0:
        print("\n⚠️ Extracted 0 rows. Printing first 80 lines of page text so we can adjust parser:\n")
        for ln in lines[:80]:
            print(ln)

if __name__ == "__main__":
    asyncio.run(main())
