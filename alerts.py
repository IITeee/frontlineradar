"""Air-raid alerts via alerts.in.ua (official alert data, token required).

The section is hidden on the site unless the ALERTS_IN_UA_TOKEN environment
variable is set (add it as a repository secret and pass it in pages.yml).
Request a token at https://alerts.in.ua/api-request. Because the site is
static and rebuilt every few hours, this is a snapshot, not a live feed.
"""
import json, os, urllib.request

API = "https://api.alerts.in.ua/v1/alerts/active.json"

def load():
    token = os.environ.get("ALERTS_IN_UA_TOKEN", "").strip()
    if not token:
        return {"enabled": False}
    req = urllib.request.Request(API, headers={"Authorization": f"Bearer {token}",
                                               "User-Agent": "frontlineradar.org (static site build)"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    rows = []
    for a in data.get("alerts", []):
        # Keep only oblast-level air-raid alerts; finer locations are not needed.
        if a.get("location_type") != "oblast":
            continue
        rows.append({"oblast": a.get("location_title") or a.get("location_oblast"),
                     "type": a.get("alert_type"), "since": a.get("started_at")})
    rows.sort(key=lambda r: r["oblast"] or "")
    return {"enabled": True, "active": rows, "source": "alerts.in.ua",
            "source_url": "https://alerts.in.ua/en"}
