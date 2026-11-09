"""Frontlineradar: fetches open sources and writes out/snapshot.json, out/newsletter.md
and out/archive/YYYY-MM-DD.json. Python standard library only.

Every source is independent: if one fails, its value from the previous snapshot
is kept and the failure is recorded in snapshot["status"].
"""
import csv, html, io, json, re, os, zipfile, datetime as dt, pathlib, urllib.request, urllib.parse
from email.utils import parsedate_to_datetime
import control, alerts

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "out"
(OUT / "archive").mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (compatible; frontlineradar.org static build; +https://frontlineradar.org/)",
      "Accept": "application/rss+xml,application/xml,text/xml,*/*"}
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)

def get(u, binary=False, timeout=40):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout).read()
    return r if binary else r.decode("utf-8", "replace")

def clean(s):
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(html.unescape(s))).strip()

def when(s):
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc).isoformat()

def rss_items(xml):
    out = []
    for it in re.findall(r"<item[\s>](.*?)</item>", xml, re.S):
        g = lambda k: (re.search(rf"<{k}[^>]*>(.*?)</{k}>", it, re.S) or [None, ""])[1]
        out.append({"title": clean(g("title")), "url": clean(g("link")), "date": when(clean(g("pubDate")))})
    for it in re.findall(r"<entry>(.*?)</entry>", xml, re.S):  # Atom
        t = re.search(r"<title[^>]*>(.*?)</title>", it, re.S)
        l = re.search(r'<link[^>]*href="([^"]+)"', it)
        u = re.search(r"<(?:published|updated)>(.*?)<", it)
        out.append({"title": clean(t.group(1) if t else ""), "url": html.unescape(l.group(1)) if l else "",
                    "date": when(u.group(1)) if u else None})
    return [x for x in out if x["title"] and x["url"].startswith("http")]

prev = {}
if (OUT / "snapshot.json").exists():
    try: prev = json.loads((OUT / "snapshot.json").read_text())
    except Exception: prev = {}
status = {}

# ---------------------------------------------------------------- headlines
# Titles and links only: no article text is copied.
FEEDS = [
    ("kyiv-independent", "Kyiv Independent", "https://kyivindependent.com/news-archive/rss/", "https://kyivindependent.com/", None),
    ("ukrinform", "Ukrinform", "https://www.ukrinform.net/rss/block-lastnews", "https://www.ukrinform.net/", None),
    ("ukrainska-pravda", "Ukrainska Pravda", "https://www.pravda.com.ua/eng/rss/", "https://www.pravda.com.ua/eng/", None),
    ("uk-mod", "UK Ministry of Defence (GOV.UK)",
     "https://www.gov.uk/search/news-and-communications.atom?organisations%5B%5D=ministry-of-defence&keywords=ukraine",
     "https://www.gov.uk/government/organisations/ministry-of-defence", None),
]
feeds = {}
prev_feeds = {f["id"]: f for f in prev.get("feeds", [])}
for fid, name, url, home, _ in FEEDS:
    try:
        items = rss_items(get(url))
        if not items: raise ValueError("feed returned no items")
        items.sort(key=lambda x: x["date"] or "", reverse=True)
        feeds[fid] = {"id": fid, "name": name, "home": home, "feed": url, "items": items[:25]}
        status[name] = "ok"
    except Exception as e:
        status[name] = f"error: {e}"[:160]
        if fid in prev_feeds:
            feeds[fid] = prev_feeds[fid]; status[name] += " (kept previous)"

# ---------------------------------------------------------------- ISW
# understandingwar.org blocks many automated clients (HTTP 403). Try its own feed
# first; fall back to Google News RSS for the title/date and rebuild ISW's URL.
MONTHS = "January February March April May June July August September October November December".split()
def isw_url(title):
    m = re.search(r"Russian Offensive Campaign Assessment,\s+(\w+) (\d{1,2}), (\d{4})", title)
    if not m: return None
    return ("https://understandingwar.org/research/russia-ukraine/russian-offensive-campaign-assessment-"
            f"{m.group(1).lower()}-{int(m.group(2))}-{m.group(3)}/")
isw = None
try:
    items = [i for i in rss_items(get("https://understandingwar.org/feed/"))
             if "Russian Offensive Campaign Assessment" in i["title"]]
    if not items: raise ValueError("no assessment in ISW feed")
    isw = {"title": items[0]["title"], "url": items[0]["url"], "date": items[0]["date"], "via": "ISW feed"}
except Exception as e1:
    try:
        q = urllib.parse.quote('"Russian Offensive Campaign Assessment" understandingwar.org')
        items = rss_items(get(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"))
        best = []
        for i in items:
            t = re.sub(r"\s+-\s+Institute for the Study of War$", "", i["title"])
            u = isw_url(t)
            if u:
                m = re.search(r"Assessment,\s+(\w+) (\d{1,2}), (\d{4})", t)
                d = dt.date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2)))
                best.append((d, t, u, i["date"]))
        if not best: raise ValueError("no assessment found via Google News")
        best.sort(reverse=True)
        d, t, u, pub = best[0]
        isw = {"title": t, "url": u, "date": pub, "covers": d.isoformat(), "via": "Google News RSS (ISW blocks automated access)"}
    except Exception as e2:
        status["ISW assessment"] = f"error: {e1} / {e2}"[:160]
if isw:
    status["ISW assessment"] = "ok"
elif prev.get("isw"):
    isw = prev["isw"]; status["ISW assessment"] += " (kept previous)"

# ---------------------------------------------------------------- strikes
# Petro Ivaniuk, "Massive Missile Attacks on Ukraine" (Kaggle, CC BY-NC-SA 4.0),
# compiled from Ukrainian Air Force reports. We publish only daily/weekly sums.
KAGGLE = "https://www.kaggle.com/api/v1/datasets/download/piterfm/massive-missile-attacks-on-ukraine"
DRONE_RX = re.compile(r"shahed|geran|uav|drone|lancet|orlan|zala|supercam|eleron|forpost|merlin|mohajer|orion|granat|kub|"
                      r"гербера|gerbera|фенікс|картограф|привет|молнія|italmas|parodiya", re.I)
def num(x):
    try: return float(x) if x not in ("", None) else 0.0
    except ValueError: return 0.0
def classify(model, cats):
    parts = [p.strip() for p in re.split(r"\s+and\s+", model or "") if p.strip()]
    kinds = set()
    for p in parts or [model or ""]:
        c = cats.get(p, "")
        if c == "UAV" or DRONE_RX.search(p): kinds.add("drone")
        elif "bomb" in (c + p).lower(): kinds.add("other")
        else: kinds.add("missile")
    return "drone" if kinds == {"drone"} else ("other" if kinds == {"other"} else "missile")
strikes = None
try:
    z = zipfile.ZipFile(io.BytesIO(get(KAGGLE, binary=True, timeout=90)))
    cats = {r["model"]: r["category"] for r in csv.DictReader(io.TextIOWrapper(z.open("missiles_and_uavs.csv"), "utf-8"))}
    daily = {}
    rows = 0
    for r in csv.DictReader(io.TextIOWrapper(z.open("missile_attacks_daily.csv"), "utf-8")):
        day = (r.get("time_end") or r.get("time_start") or "")[:10]
        try: dt.date.fromisoformat(day)
        except ValueError: continue
        k = classify(r.get("model"), cats)
        if k == "other": continue
        d = daily.setdefault(day, {"drones_launched": 0, "drones_destroyed": 0, "missiles_launched": 0, "missiles_destroyed": 0})
        d[f"{k}s_launched"] += num(r.get("launched")); d[f"{k}s_destroyed"] += num(r.get("destroyed"))
        rows += 1
    days = sorted(daily)
    series = [{"date": d, **{k: int(round(v)) for k, v in daily[d].items()}} for d in days]
    weekly = {}
    for s in series:
        d = dt.date.fromisoformat(s["date"]); wk = (d - dt.timedelta(days=d.weekday())).isoformat()
        w = weekly.setdefault(wk, {"week": wk, "drones_launched": 0, "drones_destroyed": 0, "missiles_launched": 0, "missiles_destroyed": 0})
        for k in ("drones_launched", "drones_destroyed", "missiles_launched", "missiles_destroyed"): w[k] += s[k]
    last = dt.date.fromisoformat(days[-1])
    by = {s["date"]: s for s in series}
    daily90 = []
    for i in range(89, -1, -1):
        d = (last - dt.timedelta(days=i)).isoformat()
        daily90.append(by.get(d, {"date": d, "drones_launched": 0, "drones_destroyed": 0, "missiles_launched": 0, "missiles_destroyed": 0}))
    def tot(rows_):
        t = {k: sum(r[k] for r in rows_) for k in ("drones_launched", "drones_destroyed", "missiles_launched", "missiles_destroyed")}
        t["launched"] = t["drones_launched"] + t["missiles_launched"]; t["destroyed"] = t["drones_destroyed"] + t["missiles_destroyed"]
        t["rate"] = round(100 * t["destroyed"] / t["launched"], 1) if t["launched"] else None
        return t
    peak = max(series, key=lambda s: s["drones_launched"] + s["missiles_launched"])
    strikes = {"source": "Petro Ivaniuk — Massive Missile Attacks on Ukraine (Kaggle), compiled from Ukrainian Air Force reports",
               "source_url": "https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine",
               "license": "CC BY-NC-SA 4.0", "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
               "rows": rows, "first_day": days[0], "last_day": days[-1],
               "latest": by[days[-1]], "last7": tot(daily90[-7:]), "prev7": tot(daily90[-14:-7]), "last30": tot(daily90[-30:]),
               "peak": {"date": peak["date"], "launched": peak["drones_launched"] + peak["missiles_launched"]},
               "daily90": daily90, "weekly": sorted(weekly.values(), key=lambda w: w["week"])}
    status["Missile & drone dataset"] = "ok"
except Exception as e:
    status["Missile & drone dataset"] = f"error: {e}"[:160]
    if prev.get("strikes"):
        strikes = prev["strikes"]; status["Missile & drone dataset"] += " (kept previous)"

# ---------------------------------------------------------------- control + alerts
try:
    ctrl = control.load(prev.get("control"))
    if not ctrl.get("available"):
        status["Territorial control"] = "unavailable"
    elif ctrl.get("stale"):
        status["Territorial control"] = "kept previous"
    else:
        status["Territorial control"] = "ok"
except Exception as e:
    ctrl = {"available": False, "note": "Control data unavailable."}; status["Territorial control"] = f"error: {e}"[:160]
try:
    alr = alerts.load()
    if alr.get("enabled"): status["alerts.in.ua"] = "ok"
except Exception as e:
    alr = {"enabled": False}; status["alerts.in.ua"] = f"error: {e}"[:160]

# ---------------------------------------------------------------- automated digest
TOPICS = [
    ("Strikes & air defence", r"drone|missile|shahed|strike|attack|air defen|ballistic|bomb|explosion|debris|intercept"),
    ("Front line", r"front|offensive|assault|advance|captur|liberat|repel|pokrovsk|kostiantynivka|kupiansk|huliaipole|zaporizhzhia|donetsk|kharkiv oblast|sumy oblast|battle|troops"),
    ("Energy & infrastructure", r"energy|power|grid|electric|blackout|outage|substation|refiner|oil|gas|bridge|railway"),
    ("Diplomacy & sanctions", r"talks|peace|ceasefire|negotiat|summit|sanction|nato|\beu\b|european|trump|putin|white house|kremlin|abu dhabi|minister"),
    ("Aid & weapons", r"aid|package|weapon|f-16|patriot|military assistance|funding|loan|\$|€|billion"),
    ("Civilians & humanitarian", r"killed|injur|civilian|wounded|evacuat|children|hospital|school|humanitarian|prisoner|exchange|\bpows?\b"),
]
cut = NOW - dt.timedelta(hours=36)
recent = []
for f in feeds.values():
    if f["id"] == "uk-mod": continue
    for it in f["items"]:
        if it["date"] and dt.datetime.fromisoformat(it["date"]) >= cut:
            recent.append({**it, "source": f["name"]})
recent.sort(key=lambda x: x["date"], reverse=True)
digest = []
counts = []
for name, rx in TOPICS:
    hits = [i for i in recent if re.search(rx, i["title"], re.I)]
    if hits: counts.append((len(hits), name, hits))
counts.sort(key=lambda c: -c[0])
used = set()
for n, name, hits in counts[:4]:
    ex = next((h for h in hits if h["url"] not in used), hits[0]); used.add(ex["url"])
    digest.append({"topic": name, "text": f"{n} of {len(recent)} headlines in the last 36 hours touch on {name.lower()}.",
                   "example": {"title": ex["title"], "url": ex["url"], "source": ex["source"]}})
if strikes:
    L, P = strikes["last7"], strikes["prev7"]
    ch = (f"{'up' if L['launched'] >= P['launched'] else 'down'} from {P['launched']:,} the week before" if P["launched"] else "")
    digest.append({"topic": "Strike data", "text":
        f"In the 7 days to {strikes['last_day']}, Ukraine's Air Force reported {L['launched']:,} Russian drones and missiles launched "
        f"({L['drones_launched']:,} drones, {L['missiles_launched']:,} missiles), {ch}; {L['rate'] if L['rate'] is not None else '–'}% were reported shot down or suppressed.".replace(", ;", ";")})
if isw:
    digest.append({"topic": "Analysis", "text": f"Latest ISW assessment: {isw['title']}.", "example": {"title": isw["title"], "url": isw["url"], "source": "Institute for the Study of War"}})

snap = {"generated": NOW.isoformat(), "status": status, "feeds": list(feeds.values()), "isw": isw,
        "strikes": strikes, "control": ctrl, "alerts": alr, "digest": digest, "recent_count": len(recent),
        "top": recent[:12]}
(OUT / "snapshot.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")

# Daily archive: the last snapshot of each UTC day, without the heavy series.
arch = {k: snap[k] for k in ("generated", "isw", "digest", "top", "recent_count")}
if strikes: arch["strikes"] = {k: strikes[k] for k in ("last_day", "latest", "last7", "prev7")}
(OUT / "archive" / f"{NOW.date().isoformat()}.json").write_text(json.dumps(arch, ensure_ascii=False, indent=1), encoding="utf-8")

# Newsletter draft (plain markdown).
md = [f"# Frontlineradar — {NOW:%d %B %Y}", "", "_Automated digest generated from public headlines and official statistics. Not edited by a human._", ""]
md += [f"- **{d['topic']}:** {d['text']}" + (f" Example: [{d['example']['title']}]({d['example']['url']}) ({d['example']['source']})" if d.get("example") and d["topic"] != "Analysis" else "") for d in digest]
md += ["", "## Top headlines", ""] + [f"- [{i['title']}]({i['url']}) — {i['source']}" for i in recent[:10]]
md += ["", "More: https://frontlineradar.org/"]
(OUT / "newsletter.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("refresh:", json.dumps(status, ensure_ascii=False))
