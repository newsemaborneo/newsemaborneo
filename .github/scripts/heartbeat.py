import os
import json
import datetime
import urllib.request

LOGIN = os.environ.get("LOGIN", "newsemaborneo")
TOKEN = os.environ["GH_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount } }
      }
    }
  }
}
"""


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
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
    weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    return cal["totalContributions"], weekly


def build(total, weekly):
    W, H, MID = 800, 190, 108
    LEFT, RIGHT = 24, 776
    n = len(weekly)
    step = (RIGHT - LEFT) / n
    peak = max(weekly) or 1

    pts = [(LEFT, MID)]
    for i, c in enumerate(weekly):
        x = LEFT + i * step
        if c > 0:
            a = 16 + 50 * (c / peak)
            pts += [
                (x + step * 0.25, MID),
                (x + step * 0.35, MID - a),
                (x + step * 0.50, MID + a * 0.45),
                (x + step * 0.62, MID),
            ]
        pts.append((x + step, MID))
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M20 0H0V20" fill="none" stroke="#FF0033" stroke-opacity="0.08"/>
    </pattern>
    <filter id="glow" x="-20%" y="-50%" width="140%" height="200%">
      <feGaussianBlur stdDeviation="3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style>text {{ font-family: monospace; font-weight: bold; }}</style>

  <rect width="{W}" height="{H}" rx="16" fill="#0D0D0D" stroke="#FF0033" stroke-opacity="0.5"/>
  <rect width="{W}" height="{H}" rx="16" fill="url(#grid)"/>

  <text x="24" y="32" fill="#FF0033" font-size="15">CONTRIBUTION HEARTBEAT</text>
  <text x="776" y="32" fill="#00F0FF" font-size="15" text-anchor="end">{total} contributions / last year</text>

  <path d="{d}" fill="none" stroke="#FF0033" stroke-opacity="0.25" stroke-width="2" stroke-linejoin="round"/>
  <path d="{d}" pathLength="1000" fill="none" stroke="#FF0033" stroke-width="3"
        stroke-linejoin="round" stroke-linecap="round" stroke-dasharray="140 860" filter="url(#glow)">
    <animate attributeName="stroke-dashoffset" values="1000;0" dur="6s" repeatCount="indefinite"/>
  </path>

  <circle cx="30" cy="170" r="5" fill="#FF0033" filter="url(#glow)">
    <animate attributeName="r" values="4;8;4" dur="0.9s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values="1;0.4;1" dur="0.9s" repeatCount="indefinite"/>
  </circle>
  <text x="46" y="175" fill="#FF0033" font-size="12">LIVE</text>
  <text x="776" y="175" fill="#888888" font-size="12" text-anchor="end">updated {today} UTC</text>
</svg>
'''


if __name__ == "__main__":
    total, weekly = fetch()
    os.makedirs("assets", exist_ok=True)
    with open("assets/heartbeat.svg", "w", encoding="utf-8") as f:
        f.write(build(total, weekly))
    print(f"OK: {total} contributions, {len(weekly)} weeks")
