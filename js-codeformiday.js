(() => {
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim();

  function toISODate(text) {
    const m = text.match(/\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b/);
    if (!m) return "";
    const months = {
      January:"01", February:"02", March:"03", April:"04", May:"05", June:"06",
      July:"07", August:"08", September:"09", October:"10", November:"11", December:"12"
    };
    return `${m[3]}-${months[m[1]]}-${String(parseInt(m[2])).padStart(2,"0")}`;
  }

  function extractDigits(row) {
    const ul = row.querySelector("ul.michigan.results.daily-4-midday");
    if (!ul) return "";
    const digits = Array.from(ul.querySelectorAll("li"))
      .map(li => clean(li.textContent))
      .filter(t => /^\d$/.test(t))
      .slice(0,4);
    return digits.length === 4 ? digits.join("") : "";
  }

  const rows = Array.from(document.querySelectorAll("tr"));
  const data = [];

  for (const row of rows) {
    const a = row.querySelector("a[href*='daily-4-midday']");
    if (!a) continue;

    const dateISO = toISODate(a.textContent);
    const number = extractDigits(row);

    if (dateISO && number) {
      // 👇 THIS LINE FORCES Excel to keep leading zeros
      data.push(`${dateISO},="${number}"`);
    }
  }

  const csv = "date,midday\n" + data.join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "mi_daily4_midday_2025.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);

  console.log("✅ Downloaded CSV with leading zeros preserved.");
})();
