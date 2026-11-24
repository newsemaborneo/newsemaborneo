import os
import json
import math
import datetime
import urllib.request

LOGIN = os.environ.get("LOGIN", "newsemaborneo")
NAME = os.environ.get("DISPLAY_NAME", "Newsem Aborneo")
TOKEN = os.environ["GH_TOKEN"]
DAYS = 31
T = 6.0  # detik untuk satu kali garis terang menyapu grafik

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

CSS = """
text { font-family: 'Segoe UI', Arial, sans-serif; font-weight: 700; }
.run { stroke-dasharray: __DASH__ __LEN__; animation: run __T__s linear infinite; }
@keyframes run { from { stroke-dashoffset: __DASH__; } to { stroke-dashoffset: -__LEN__; } }
.dot { transform-box: fill-box; transform-origin: center; animation: beat __T__s linear infinite; }
@keyframes beat {
  0% { transform: scale(1); } 3% { transform: scale(1.9); } 6% { transform: scale(1.1); }
  9% { transform: scale(1.6); } 14%, 100% { transform: scale(1); }
}
.area { animation: breathe 1.2s ease-in-out infinite; }
@keyframes breathe { 0%, 100% { opacity: .55; } 25% { opacity: 1; } 55% { opacity: .55; } 75% { opacity: .85; } }
.live { transform-box: fill-box; transform-origin: center; animation: lub 1.2s ease-in-out infinite; }
@keyframes lub { 0%, 100% { transform: scale(.8); } 25% { transform: scale(1.5); } 55% { transform: scale(.9); } 75% { transform: scale(1.3); } }
"""


def fetch():
    now = datetime.datetime.utcnow()
    today = now.date()
    start = today - datetime.timedelta(days=DAYS - 1)
    variables = {
        "login": LOGIN,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    body = json.dumps({"query": QUERY, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "heartbeat-graph",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(payload["errors"])
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    counts = {}
    for w in cal["weeks"]:
        for d in w["contributionDays"]:
            counts[d["date"]] = d["contributionCount"]
    days = [start + datetime.timedelta(days=i) for i in range(DAYS)]
    return days, [counts.get(d.isoformat(), 0) for d in days]


def spline(pts, top, bottom, steps=10):
    """Catmull-Rom: kurva mulus melewati semua titik data."""
    out, marks = [], []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        marks.append(len(out))
        for s in range(steps):
            t = s / steps
            c = []
            for k in (0, 1):
                v = 0.5 * (
                    2 * p1[k]
                    + (-p0[k] + p2[k]) * t
                    + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t
                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3
                )
                c.append(v)
            c[1] = min(max(c[1], top), bottom)
            out.append((c[0], c[1]))
    marks.append(len(out))
    out.append(pts[-1])
    return out, marks


def build(days, values):
    W, H = 1060, 365
    PL, PR, PT, PB = 85, 1020, 65, 303
    total = sum(values)

    step = 10 if max(values) > 30 else 5
    ymax = max(step, math.ceil(max(values) / step) * step)

    def xy(i, v):
        return PL + i * (PR - PL) / (DAYS - 1), PB - v / ymax * (PB - PT)

    pts = [xy(i, v) for i, v in enumerate(values)]
    poly, marks = spline(pts, PT, PB)

    cum = [0.0]
    for a, b in zip(poly, poly[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    length = cum[-1]
    dash = 150.0

    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in poly)
    area = d + f" L{PR:.1f},{PB} L{PL:.1f},{PB} Z"

    parts = []

    for v in range(0, ymax + 1, step):
        y = PB - v / ymax * (PB - PT)
        parts.append(f'<line x1="{PL}" y1="{y:.1f}" x2="{PR}" y2="{PB - (v / ymax) * (PB - PT) - 0:.1f}" stroke="#FF0033" stroke-opacity="0.14" stroke-dasharray="3 4"/>')
        parts.append(f'<text x="{PL - 12}" y="{y + 4:.1f}" fill="#FF0033" font-size="12" text-anchor="end">{v}</text>')

    for i, day in enumerate(days):
        x = PL + i * (PR - PL) / (DAYS - 1)
        parts.append(f'<line x1="{x:.1f}" y1="{PT}" x2="{x:.1f}" y2="{PB}" stroke="#FF0033" stroke-opacity="0.08" stroke-dasharray="3 4"/>')
        parts.append(f'<text x="{x:.1f}" y="{PB + 20}" fill="#FF0033" font-size="12" text-anchor="middle">{day.day}</text>')

    parts.append(f'<path class="area" d="{area}" fill="url(#fill)"/>')
    parts.append(f'<path d="{d}" fill="none" stroke="#FF0033" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>')
    parts.append(f'<path class="run" d="{d}" fill="none" stroke="#FF99AA" stroke-width="4" stroke-linejoin="round" stroke-linecap="round" filter="url(#glow)"/>')

    for i, (x, y) in enumerate(pts):
        arc = cum[marks[i]]
        delay = arc / (length + dash) * T
        parts.append(f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#00F0FF" style="animation-delay:{delay:.2f}s"/>')

    css = (
        CSS.replace("__DASH__", f"{dash:.1f}")
        .replace("__LEN__", f"{length:.1f}")
        .replace("__T__", f"{T:.1f}")
    )
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FF0033" stop-opacity="0.35"/>
      <stop offset="1" stop-color="#FF0033" stop-opacity="0.02"/>
    </linearGradient>
    <filter id="glow" x="-10%" y="-30%" width="120%" height="160%">
      <feGaussianBlur stdDeviation="3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style>{css}</style>

  <rect width="{W}" height="{H}" rx="14" fill="#141414"/>

  <text x="{W / 2}" y="34" fill="#FF0033" font-size="19" text-anchor="middle">{NAME}’s Contribution Heartbeat</text>
  <text x="{W / 2}" y="52" fill="#00F0FF" font-size="12" text-anchor="middle">{total} contributions · last {DAYS} days</text>

  <text x="30" y="{(PT + PB) / 2}" fill="#FF0033" font-size="12" text-anchor="middle" transform="rotate(-90 30 {(PT + PB) / 2})">Contributions</text>
  <text x="{(PL + PR) / 2}" y="{PB + 52}" fill="#FF0033" font-size="12" text-anchor="middle">Days</text>

  {chr(10).join("  " + p for p in parts)}

  <circle class="live" cx="{PR - 58}" cy="30" r="5" fill="#FF0033" filter="url(#glow)"/>
  <text x="{PR - 46}" y="34" fill="#FF0033" font-size="12">LIVE</text>
  <text x="{PR}" y="{H - 12}" fill="#666666" font-size="11" text-anchor="end">updated {today} UTC</text>
</svg>
'''


if __name__ == "__main__":
    days, values = fetch()
    os.makedirs("assets", exist_ok=True)
    with open("assets/heartbeat.svg", "w", encoding="utf-8") as f:
        f.write(build(days, values))
    print(f"OK: {sum(values)} contributions in {DAYS} days, max/day = {max(values)}")
