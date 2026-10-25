"""Render a static SVG of one year's GitHub contributions.

Reads the public contribution calendar (no token needed) and writes
assets/contributions-<year>.svg with the yearly total, streaks and a heatmap.
"""
import datetime as dt
import html
import re
import sys
import urllib.request
from pathlib import Path

USER = "AdityaWagh06"
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today().year
OUT = Path(__file__).resolve().parent.parent / "assets" / f"contributions-{YEAR}.svg"

BG, BORDER, TEXT, MUTED, ACCENT = "#0d1117", "#30363d", "#e6edf3", "#8b949e", "#39d353"
LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
CELL, GAP = 11, 3


def fetch_days():
    url = f"https://github.com/users/{USER}/contributions?from={YEAR}-01-01&to={YEAR}-12-31"
    req = urllib.request.Request(url, headers={"User-Agent": "contributions-card"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

    levels = {}  # cell id -> (date, level)
    for m in re.finditer(r'data-date="(\d{4}-\d{2}-\d{2})"\s+id="([^"]+)"\s+data-level="(\d)"', page):
        levels[m.group(2)] = (dt.date.fromisoformat(m.group(1)), int(m.group(3)))

    counts = {}  # cell id -> count, from the tooltip text
    for m in re.finditer(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        n = re.match(r"([\d,]+) contribution", m.group(2))
        counts[m.group(1)] = int(n.group(1).replace(",", "")) if n else 0

    days = {d: (counts.get(cid, 0), lvl) for cid, (d, lvl) in levels.items() if d.year == YEAR}
    if not days:
        sys.exit("No contribution data found; GitHub's page layout may have changed.")
    return days


def streaks(days, today):
    longest = run = 0
    for d in sorted(days):
        if d > today:
            break
        run = run + 1 if days[d][0] else 0
        longest = max(longest, run)

    current, d = 0, today
    if not days.get(d, (0,))[0]:
        d -= dt.timedelta(days=1)  # today can still be empty without breaking the streak
    while d in days and days[d][0]:
        current += 1
        d -= dt.timedelta(days=1)
    return current, longest


def render(days):
    today = min(dt.date.today(), dt.date(YEAR, 12, 31))
    total = sum(c for c, _ in days.values())
    active = sum(1 for c, _ in days.values() if c)
    current, longest = streaks(days, today)

    jan1 = dt.date(YEAR, 1, 1)
    first_sunday = jan1 - dt.timedelta(days=(jan1.weekday() + 1) % 7)
    weeks = (dt.date(YEAR, 12, 31) - first_sunday).days // 7 + 1

    left, top = 40, 118
    width = left + weeks * (CELL + GAP) + 24
    height = top + 7 * (CELL + GAP) + 40

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="{left}" y="34" fill="{TEXT}" font-size="16" font-weight="600">{YEAR} Contributions</text>',
    ]

    stats = [(f"{total:,}", "contributions"), (str(active), "active days"),
             (f"{current} days", "current streak"), (f"{longest} days", "longest streak")]
    col = (width - left - 24) / len(stats)
    for i, (value, label) in enumerate(stats):
        x = left + i * col
        parts.append(f'<text x="{x:.0f}" y="70" fill="{ACCENT}" font-size="22" font-weight="700">{html.escape(value)}</text>')
        parts.append(f'<text x="{x:.0f}" y="90" fill="{MUTED}" font-size="12">{label}</text>')

    for name, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        y = top + row * (CELL + GAP) + CELL - 2
        parts.append(f'<text x="8" y="{y}" fill="{MUTED}" font-size="10">{name}</text>')

    for month in range(1, 13):
        first = dt.date(YEAR, month, 1)
        x = left + ((first - first_sunday).days // 7) * (CELL + GAP)
        parts.append(f'<text x="{x}" y="{top - 8}" fill="{MUTED}" font-size="10">{first:%b}</text>')

    d = jan1
    while d.year == YEAR:
        week, row = (d - first_sunday).days // 7, (d.weekday() + 1) % 7
        count, level = days.get(d, (0, 0))
        fill = LEVELS[level] if d <= today else "none"
        stroke = "" if d <= today else f' stroke="{LEVELS[0]}"'
        parts.append(f'<rect x="{left + week * (CELL + GAP)}" y="{top + row * (CELL + GAP)}" width="{CELL}" '
                     f'height="{CELL}" rx="2" fill="{fill}"{stroke}><title>{count} on {d:%b %d}</title></rect>')
        d += dt.timedelta(days=1)

    legend_x, legend_y = width - 24 - 5 * (CELL + GAP) - 64, height - 18
    parts.append(f'<text x="{legend_x}" y="{legend_y + 9}" fill="{MUTED}" font-size="10">Less</text>')
    for i, colour in enumerate(LEVELS):
        parts.append(f'<rect x="{legend_x + 28 + i * (CELL + GAP)}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" fill="{colour}"/>')
    parts.append(f'<text x="{legend_x + 32 + 5 * (CELL + GAP)}" y="{legend_y + 9}" fill="{MUTED}" font-size="10">More</text>')
    parts.append(f'<text x="{left}" y="{legend_y + 9}" fill="{MUTED}" font-size="10">Updated {dt.date.today():%b %d, %Y}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(fetch_days()), encoding="utf-8")
    print(f"Wrote {OUT}")
