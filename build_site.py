"""Frontlineradar: renders site/ from out/snapshot.json and out/archive/*.json.

Writes site/index.html, /daily-brief/, /strikes/, /front-line-map/, /brief/YYYY-MM-DD/,
site/assets/data.js, site/sitemap.xml, site/robots.txt and site/CNAME.
"""
import json, re, html, pathlib, shutil, datetime as dt
from email.utils import format_datetime

ROOT = pathlib.Path(__file__).resolve().parent
SITE = "https://frontlineradar.org"
NAME = "Frontlineradar"
OUTD = ROOT / "site"
snap = json.loads((ROOT / "out/snapshot.json").read_text(encoding="utf-8"))
E = lambda s: html.escape(str(s if s is not None else ""), quote=True)
GEN = dt.datetime.fromisoformat(snap["generated"])
UPDATED = GEN.strftime("%Y-%m-%d %H:%M UTC")
UPDATED_ISO = GEN.isoformat()
TODAY = GEN.date().isoformat()
TODAY_H = f"{GEN.day} {GEN:%B %Y}"
st = snap.get("strikes")
isw = snap.get("isw")
ctrl = snap.get("control") or {"available": False}
alr = snap.get("alerts") or {"enabled": False}

def fmt_dt(iso):
    try: return dt.datetime.fromisoformat(iso).strftime("%d %b, %H:%M UTC")
    except Exception: return ""
def n(x): return f"{x:,}" if isinstance(x, (int, float)) else "–"
def pretty_day(iso):
    d = dt.date.fromisoformat(iso); return f"{d.day} {d:%B %Y}"
def clip(s, n=158):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    if len(s) <= n: return s
    cut = s[:n - 1].rsplit(" ", 1)[0]
    return (cut or s[:n - 1]).rstrip(".,;:") + "…"
def xml_esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))
def ldjson(obj): return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c") + "</script>"

DISCLAIMER = ('<div class="disclaimer"><strong>Estimates, not real-time intelligence.</strong> Everything here comes from official '
              'statements and open-source (OSINT) reporting, is delayed by hours to days, and is attributed to its source. '
              'Figures are reported claims and may be revised.</div>'
              '<div class="disclaimer safety"><strong>No live military positions.</strong> This site does not publish unit locations, '
              'troop movements or anything that could help target people. It only links to published reporting and aggregates '
              'official statistics after the fact.</div>')

ORG = {"@type": "Organization", "@id": SITE + "/#org", "name": NAME, "url": SITE + "/",
       "logo": {"@type": "ImageObject", "url": SITE + "/assets/og.png"}}
FAQ = [
    ("What is Frontlineradar?", "Frontlineradar is a free daily radar of the Russia–Ukraine war. It collects headlines from Ukrainian and international outlets, links the latest Institute for the Study of War (ISW) assessment, and charts Russian drone and missile attacks reported by Ukraine's Air Force. It is rebuilt every six hours."),
    ("Does Frontlineradar show real-time troop positions?", "No. The site never shows live unit locations or troop movements. It only aggregates official statistics and links to published reporting, which is delayed by hours or days."),
    ("Where does the drone and missile data come from?", "Daily launches and interceptions come from the open dataset 'Massive Missile Attacks on Ukraine' by Petro Ivaniuk, compiled from Ukrainian Air Force reports and licensed CC BY-NC-SA 4.0. Frontlineradar only publishes daily and weekly totals."),
    ("Who controls which areas of Ukraine?", "The front-line map draws area-level territorial control from VIINA 2.0 (Zhukov & Ayers), licensed under the Open Database License (ODbL). Populated-place assessments are merged and simplified. The layer is delayed by days and approximate. It does not show military units or movements."),
    ("How is the daily brief written?", "The daily brief is an automated digest. It groups the latest headlines by keyword into topics such as strikes, front line, energy and diplomacy, and adds the weekly strike numbers. It is not edited by a human and links to the original articles."),
    ("How often is the site updated?", "Every six hours. Each page shows the time of the latest snapshot in UTC."),
]

# ------------------------------------------------------------------ layout
NAV = [("Brief", "daily-brief/"), ("Archive", "brief/"), ("Strikes", "strikes/"), ("Map", "front-line-map/"), ("FAQ", "#faq"), ("Sources", "#method")]
def page(path, title, desc, body, ld, og_type="website", extra_head="", published=None, modified=None):
    depth = path.count("/")
    pre = "../" * depth
    canon = f"{SITE}/{path}"
    nav = "".join(f'<a href="{(pre if not h.startswith("#") else pre if depth else "") + h}">{E(t)}</a>' for t, h in NAV)
    article = ""
    if published: article += f'<meta property="article:published_time" content="{E(published)}">'
    if modified: article += f'<meta property="article:modified_time" content="{E(modified)}">'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canon}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#0b0e14" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f6f7fb" media="(prefers-color-scheme: light)">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{NAME}">
<meta property="og:locale" content="en_US">
<meta property="og:url" content="{canon}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{SITE}/assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Frontlineradar — Ukraine war daily radar">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{SITE}/assets/og.png">
<link rel="icon" href="{pre}favicon.svg" type="image/svg+xml">
<link rel="manifest" href="{pre}manifest.webmanifest">
<link rel="alternate" type="application/rss+xml" title="Frontlineradar Ukraine war daily briefs" href="{SITE}/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet" media="print" onload="this.media='all'">
<noscript><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet"></noscript>
<link rel="stylesheet" href="{pre}assets/style.css">
{article}
<script>try{{document.documentElement.dataset.theme=localStorage.frTheme||(matchMedia("(prefers-color-scheme: light)").matches?"light":"dark")}}catch(e){{}}</script>
{ldjson(ld)}
{extra_head}
</head>
<body>
<header class="nav"><div class="wrap nav-in">
  <a class="brand" href="{pre or './'}"><span class="pulse"></span>{NAME}</a>
  <nav>{nav}<a href="{pre}#community">Community</a><a class="cta" href="{pre}#newsletter">Subscribe</a></nav>
  <button id="theme" aria-label="Toggle theme">◐</button>
</div></header>
{body}
<footer><div class="wrap">
<p>{NAME} · Daily OSINT and official-source radar of the war in Ukraine · No real-time military positions · Updated {E(UPDATED)}</p>
<nav class="foot-links" aria-label="Site pages"><a href="{pre or './'}">Home</a><a href="{pre}daily-brief/">Daily brief</a><a href="{pre}brief/">Brief archive</a><a href="{pre}strikes/">Drone &amp; missile strikes</a><a href="{pre}front-line-map/">Ukraine front line map</a><a href="{SITE}/feed.xml">RSS</a></nav>
<p>Strike statistics: Petro Ivaniuk, “Massive Missile Attacks on Ukraine” (CC BY-NC-SA 4.0); derived totals on this site are shared under the same licence. Headlines link to and belong to their publishers.</p>
<p>Privacy-friendly, cookie-free analytics by GoatCounter.</p>
</div></footer>
<script defer src="{pre}assets/data.js"></script>
<script defer src="{pre}assets/app.js"></script>
<script data-goatcounter="https://frontlineradar.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body></html>
'''

# ------------------------------------------------------------------ fragments
def digest_html(digest, pre=""):
    if not digest: return '<p class="muted">No digest in this snapshot.</p>'
    li = []
    for d in digest:
        ex = d.get("example")
        exs = (f'<span class="ex">e.g. <a href="{E(ex["url"])}" rel="noopener" target="_blank">{E(ex["title"])}</a> — {E(ex["source"])}</span>'
               if ex and d["topic"] != "Analysis" else "")
        txt = E(d["text"])
        if d["topic"] == "Analysis" and ex:
            txt = f'Latest ISW assessment: <a href="{E(ex["url"])}" rel="noopener" target="_blank">{E(ex["title"])}</a>.'
        elif d["topic"] == "Strike data":
            txt += f' <a href="{pre}strikes/">Charts</a>.'
        li.append(f"<li><b>{E(d['topic'])}:</b> {txt}{exs}</li>")
    return '<p class="auto-label">Automated digest · generated from headlines and official statistics by keyword rules · not edited by a human</p><ul class="digest">' + "".join(li) + "</ul>"

def heads_html(items, with_source=True):
    if not items: return '<p class="muted">No headlines in this snapshot.</p>'
    return '<ul class="heads">' + "".join(
        f'<li><a href="{E(i["url"])}" rel="noopener" target="_blank">{E(i["title"])}</a>'
        f'<small>{E(i.get("source","")) + " · " if with_source and i.get("source") else ""}{E(fmt_dt(i.get("date") or ""))}</small></li>' for i in items) + "</ul>"

def isw_html():
    if not isw:
        return '<div class="card isw"><div><h3>ISW daily assessment</h3><p class="muted">Not available in this snapshot.</p></div><a class="btn" href="https://understandingwar.org/research/russia-ukraine/" target="_blank" rel="noopener">ISW Russia–Ukraine research</a></div>'
    return (f'<div class="card isw"><div><h3>Institute for the Study of War — latest assessment</h3><p style="margin:0">{E(isw["title"])}'
            f'<br><small class="muted">Published {E(fmt_dt(isw.get("date") or ""))} · Link only; read the full analysis and maps on ISW’s site.</small></p></div>'
            f'<a class="btn" href="{E(isw["url"])}" target="_blank" rel="noopener">Read on understandingwar.org</a></div>')

def metrics_html(pre=""):
    if not st:
        return '<div class="metrics"><div class="metric"><div class="v">–</div><div class="l">Strike data unavailable</div></div></div>'
    L, P, lt = st["last7"], st["prev7"], st["latest"]
    ch = (L["launched"] - P["launched"]) / P["launched"] * 100 if P["launched"] else None
    chs = f'{"+" if ch is not None and ch >= 0 else ""}{ch:.0f}% vs previous 7 days' if ch is not None else "No comparison"
    lat = lt["drones_launched"] + lt["missiles_launched"]; latd = lt["drones_destroyed"] + lt["missiles_destroyed"]
    rate = L["rate"] or 0
    return f'''<div class="metrics">
<div class="metric"><div class="v">{n(L["launched"])}</div><div class="l">Drones &amp; missiles launched, 7 days</div><div class="d">{E(chs)} · to {E(st["last_day"])}</div></div>
<div class="metric"><div class="v">{rate:.0f}%</div><div class="l">Reported shot down or suppressed</div><div class="d">{n(L["destroyed"])} of {n(L["launched"])}, last 7 days</div><div class="bar"><i style="width:{min(100,rate):.0f}%"></i></div></div>
<div class="metric"><div class="v">{n(lat)}</div><div class="l">Latest reported day</div><div class="d">{E(st["last_day"])}: {n(lt["drones_launched"])} drones, {n(lt["missiles_launched"])} missiles, {n(latd)} downed</div></div>
<div class="metric"><div class="v">{n(L["missiles_launched"])}</div><div class="l">Missiles, 7 days</div><div class="d">{n(L["missiles_destroyed"])} reported intercepted · <a href="{pre}strikes/">charts</a></div></div>
</div>'''

def strikes_section(pre="", full=False):
    if not st:
        return '<div class="card"><div class="placeholder">Strike data could not be loaded in this snapshot. The chart returns automatically when the dataset is reachable again.</div></div>'
    note = (f'<p class="note">Source: <a href="{E(st["source_url"])}" target="_blank" rel="noopener">Petro Ivaniuk, “Massive Missile Attacks on Ukraine”</a> (Kaggle), compiled from Ukrainian Air Force reports, '
            f'licensed <a href="{E(st["license_url"])}" target="_blank" rel="noopener">{E(st["license"])}</a>. Frontlineradar shows daily and weekly sums only; these derived totals are shared under the same licence. '
            f'“Downed” means reported shot down or suppressed by electronic warfare. Days are grouped by the end time of each Air Force report. Data from {E(st["first_day"])} to {E(st["last_day"])}.</p>')
    table = ""
    if full:
        rows = "".join(f'<tr><td>{E(w["week"])}</td><td class="num">{n(w["drones_launched"])}</td><td class="num">{n(w["drones_destroyed"])}</td>'
                       f'<td class="num">{n(w["missiles_launched"])}</td><td class="num">{n(w["missiles_destroyed"])}</td></tr>'
                       for w in reversed(st["weekly"][-26:]))
        table = ('<div class="card"><h3>Weekly totals, last 26 weeks</h3><div class="table-wrap"><table><thead><tr><th scope="col">Week starting</th>'
                 '<th scope="col">Drones launched</th><th scope="col">Drones downed</th><th scope="col">Missiles launched</th><th scope="col">Missiles downed</th></tr></thead>'
                 f'<tbody>{rows}</tbody></table></div></div>')
    return (f'<div class="card"><div class="seg" role="group" aria-label="Chart range"><button type="button" data-range="daily" aria-pressed="true">Daily, 90 days</button>'
            f'<button type="button" data-range="weekly" aria-pressed="false">Weekly, all</button></div>'
            f'<div class="chart-box"><canvas id="strikeChart" aria-label="Bar chart of Russian drones and missiles launched at Ukraine and the number reported shot down"></canvas></div>{note}</div>{table}')

ODBL = "https://opendatacommons.org/licenses/odbl/1-0/"
VIINA = "https://github.com/zhukovyuri/VIINA"
LEAFLET = ('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">'
           '<script defer src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>')
def map_ready():
    return bool(ctrl.get("available") and (ROOT / "out/control.geojson").exists())
def map_section(pre="", compact=False):
    if not map_ready():
        return ('<div class="card"><div class="placeholder"><p>The territorial-control layer is unavailable in this snapshot. '
                'The last derived map is published again automatically when VIINA can be downloaded.</p></div></div>')
    try: as_h = pretty_day(ctrl.get("as_of") or "")
    except Exception: as_h = ctrl.get("as_of") or ""
    areas = ctrl.get("area_km2") or {}
    def km(key):
        v = areas.get(key)
        return f"{round(v):,} km²" if isinstance(v, (int, float)) else "–"
    stale = ('<p class="note">The latest VIINA download failed, so this is the last derived layer.</p>'
             if ctrl.get("stale") else "")
    cls = "control-map compact" if compact else "control-map"
    return f'''<div class="card map-card">
<div class="{cls}" data-control-map data-src="{pre}assets/control.geojson" role="img" aria-label="Area-level map of assessed control in Ukraine: Russian-controlled, contested, and Ukrainian-controlled. Not military unit locations."></div>
<div class="legend"><span><i style="background:#d4524a"></i>Russian-controlled</span><span><i style="background:#f0b429"></i>Contested</span><span><i style="background:#7eb6e6"></i>Ukrainian-controlled</span></div>
</div>
<p class="note"><b>Data as of {E(as_h)}.</b> Area-level, delayed, and approximate. Cells around populated places are merged by assessed status and simplified. This is not a live front line and it does not show units or movements.</p>
{stale}
<p class="note">Approximate cell area: Russian-controlled {km("RU")}, contested {km("CONTESTED")}, Ukrainian-controlled {km("UA")}.</p>
<p class="note">Territorial control: VIINA 2.0 (Zhukov &amp; Ayers), <a href="{VIINA}">{VIINA}</a> — contains information from VIINA, made available under the <a href="{ODBL}">Open Database License (ODbL)</a>. The derived file <a href="{pre}assets/control.geojson">control.geojson</a> is published under the ODbL as well.</p>'''

def alerts_section():
    if not alr.get("enabled"): return ""
    rows = alr.get("active") or []
    body = ("".join(f'<span class="chip"><b>{E(r["oblast"])}</b>{E(r["type"] or "")}</span>' for r in rows)
            if rows else '<span class="muted">No active oblast-level alerts at snapshot time.</span>')
    return (f'<section id="alerts"><div class="sec-head"><h2>Air-raid alerts</h2><p>Oblasts with an active alert when this page was built ({E(UPDATED)}). '
            f'This is a snapshot, not a live feed — use the official Air Alert app for safety.</p></div>'
            f'<div class="card"><div class="chips">{body}</div><p class="note">Source: <a href="{E(alr["source_url"])}">alerts.in.ua</a>.</p></div></section>')

def feeds_html():
    cards = []
    for f in snap.get("feeds", []):
        cards.append(f'<div class="card"><h3><a href="{E(f["home"])}" target="_blank" rel="noopener">{E(f["name"])}</a></h3>{heads_html(f["items"][:8], with_source=False)}</div>')
    return '<div class="feed-grid">' + "".join(cards) + "</div>"

def news_ld(path, headline, desc, published, modified):
    return {"@type": "NewsArticle", "headline": headline[:110], "description": clip(desc, 200), "datePublished": published, "dateModified": modified,
            "inLanguage": "en", "mainEntityOfPage": f"{SITE}/{path}", "isAccessibleForFree": True,
            "image": {"@type": "ImageObject", "url": f"{SITE}/assets/og.png", "width": 1200, "height": 630},
            "author": {"@type": "Organization", "name": NAME, "url": SITE + "/"}, "publisher": ORG,
            "about": [{"@type": "Thing", "name": "Russian invasion of Ukraine"}]}
def crumbs_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i, "name": nme, "item": u} for i, (nme, u) in enumerate(items, 1)]}

# ------------------------------------------------------------------ archive
arch_dir = ROOT / "out/archive"
archive = sorted((json.loads(p.read_text(encoding="utf-8")) | {"day": p.stem}) for p in arch_dir.glob("*.json")) if arch_dir.exists() else []
archive = sorted(archive, key=lambda a: a["day"], reverse=True)
first_today = TODAY + "T00:00:00+00:00"

# ------------------------------------------------------------------ index
brief_h1 = f"Ukraine war daily brief — {TODAY_H}"
home_title = f"Ukraine war update today | {NAME}"
home_desc = clip("Russia–Ukraine war update today: the daily brief, Ukraine front line map, and drone and missile strike charts. Delayed official and OSINT sources. No live unit locations.")
faq_html = "".join(f"<h3>{E(q)}</h3><p>{E(a)}</p>" for q, a in FAQ)
status_html = "".join(f'<span class="chip" style="color:{"var(--low)" if v=="ok" else "var(--mid)" if v.startswith("stub") or v.startswith("kept") else "var(--high)"}">● {E(k)}: {E(v)}</span>' for k, v in snap["status"].items())
SOURCES = [("Kyiv Independent", "https://kyivindependent.com/", "Headlines via RSS (titles and links only)"),
           ("Ukrinform", "https://www.ukrinform.net/", "Ukraine's national news agency, headlines via RSS"),
           ("Ukrainska Pravda", "https://www.pravda.com.ua/eng/", "Headlines via RSS"),
           ("UK Ministry of Defence (GOV.UK)", "https://www.gov.uk/government/organisations/ministry-of-defence", "Ukraine-related MoD news via the GOV.UK Atom feed. Defence Intelligence updates are published on X (@DefenceHQ)."),
           ("Institute for the Study of War", "https://understandingwar.org/research/russia-ukraine/", "Link to the latest Russian Offensive Campaign Assessment"),
           ("Massive Missile Attacks on Ukraine", "https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine", "Petro Ivaniuk, from Ukrainian Air Force reports, CC BY-NC-SA 4.0"),
           ("VIINA 2.0 (Zhukov & Ayers)", "https://github.com/zhukovyuri/VIINA", "Territorial control of populated places, dissolved on the front-line map, ODbL")]
src_html = "".join(f'<li><a href="{E(u)}" target="_blank" rel="noopener">{E(t)}</a><small>{E(d)}</small></li>' for t, u, d in SOURCES)
home_ld = {"@context": "https://schema.org", "@graph": [
    {"@type": "WebSite", "@id": SITE + "/#site", "name": NAME, "url": SITE + "/", "description": home_desc, "inLanguage": "en",
     "publisher": {"@id": SITE + "/#org"}},
    ORG,
    {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]},
    crumbs_ld([(NAME, SITE + "/")])]}
home_body = f'''<section class="hero" id="top"><div class="wrap">
  <p class="eyebrow">Ukraine war radar · Updated <span id="updated-static">{E(UPDATED)}</span></p>
  <h1>Ukraine war update <span class="grad">today</span></h1>
  <p class="lede">A Russia–Ukraine war update today: the <a href="daily-brief/">Ukraine war daily brief</a>, an area-level <a href="front-line-map/">Ukraine front line map</a>, and <a href="strikes/">drone and missile strike</a> charts. Sources are official or open, and everything is delayed. No live unit locations.</p>
  {metrics_html()}
  {DISCLAIMER}
</div></section>
<main class="wrap">
  <section id="brief"><div class="sec-head"><h2>Ukraine war daily brief — {E(TODAY_H)}</h2><p>What the headlines of the last 36 hours are about. <a href="daily-brief/">Open the full brief</a> or browse the <a href="brief/">archive</a>.</p></div>
    <div class="grid2"><div class="card">{digest_html(snap.get("digest"))}</div><div class="card"><h3>Top headlines</h3>{heads_html(snap.get("top", [])[:8])}</div></div>
  </section>
  <section id="isw" style="padding-top:0">{isw_html()}</section>
  <section id="strikes"><div class="sec-head"><h2>Drone and missile attacks</h2><p>Russian drones and missiles launched at Ukraine, and how many Ukraine’s Air Force reported shot down or suppressed.</p></div>{strikes_section()}</section>
  <section id="control"><div class="sec-head"><h2>Ukraine front line map</h2><p>Area-level territorial control from VIINA 2.0, delayed and approximate. It is not a live war map and it does not show units or movements. <a href="front-line-map/">Open the Ukraine front line map</a>.</p></div>{map_section(compact=True)}</section>
  {alerts_section()}
  <section id="sources-feed"><div class="sec-head"><h2>Latest by source</h2><p>Titles and links only — read the full stories on the publishers’ sites.</p></div>{feeds_html()}</section>
  <section id="newsletter"><div class="card news">
    <div><h2>Get the daily brief</h2><p>One short email a day: strikes, front-line headlines and the latest ISW assessment.</p></div>
    <form id="signup"><input type="email" required placeholder="you@example.com" aria-label="Email"><button>Subscribe</button></form>
    <p id="signup-msg" class="signup-msg" role="status"></p>
  </div></section>
  <section id="faq"><div class="sec-head"><h2>FAQ</h2></div><div class="card" id="faq-list">{faq_html}</div></section>
  <section id="method"><div class="sec-head"><h2>Sources and method</h2><p>Refreshed every six hours by GitHub Actions. If a source fails, its last good data is kept and flagged below.</p></div>
    <div class="grid2"><div class="card"><h3>Sources</h3><ul class="sources">{src_html}</ul></div>
    <div class="card"><h3>Source status at last build</h3><div class="chips">{status_html}</div>
    <p class="note">The daily brief is generated by keyword rules from headline titles. No article text is copied. Strike totals are reported claims by Ukraine’s Air Force and can be revised.</p></div></div>
  </section>
  <section id="community"><div class="sec-head"><h2>Community</h2><p>Discuss sources and data. Be respectful, cite sources, and never post locations of military units or movements. Comments are moderated.</p></div>
    <div class="card"><div class="topic-tabs" id="topic-tabs" role="tablist"></div><div id="giscus"></div><p class="community-soon" id="community-soon" hidden>Comments open soon.</p></div>
  </section>
</main>'''
CHART = '<script defer src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>'
(OUTD / "index.html").write_text(page("", home_title, home_desc, home_body, home_ld, extra_head=CHART + (LEAFLET if map_ready() else "")), encoding="utf-8")

# ------------------------------------------------------------------ daily brief (+ archive)
def brief_links(pre, day, is_today):
    days = [a["day"] for a in archive]
    older = newer = ""
    if is_today:
        older_day = next((d for d in days if d < TODAY), None)
        if older_day:
            older = f'<a rel="prev" href="{pre}brief/{older_day}/">← {E(pretty_day(older_day))}</a>'
    elif day in days:
        i = days.index(day)
        if i + 1 < len(days):
            od = days[i + 1]
            older = f'<a rel="prev" href="{pre}brief/{od}/">← {E(pretty_day(od))}</a>'
        if i > 0:
            nd = days[i - 1]
            newer = f'<a rel="next" href="{pre}brief/{nd}/">{E(pretty_day(nd))} →</a>'
        elif day < TODAY:
            newer = f'<a rel="next" href="{pre}daily-brief/">Current brief →</a>'
    if is_today and any(d == TODAY for d in days):
        perm = f'<a href="{pre}brief/{TODAY}/">Permanent link: {E(TODAY_H)}</a>'
    elif not is_today and day == TODAY:
        perm = f'<a href="{pre}daily-brief/">Updating brief for today</a>'
    else:
        perm = ""
    related = (f'<nav class="related" aria-label="Related pages">'
               f'<a href="{pre}front-line-map/">Ukraine front line map</a>'
               f'<a href="{pre}strikes/">Drone and missile strikes</a>'
               f'<a href="{pre}brief/">Brief archive</a>{perm}</nav>')
    pager = f'<nav class="pager" aria-label="Earlier and later briefs">{older or "<span></span>"}{newer or "<span></span>"}</nav>'
    return related + pager

def brief_desc(digest, day_h, archived):
    lead = (digest[0]["text"] if digest else "").strip()
    tail = f"Archived Ukraine war update for {day_h}." if archived else f"Ukraine war daily brief for {day_h}, updated through the day."
    return clip((lead + " " + tail).strip() if lead else tail)

def brief_body(pre, day_h, digest, top, isw_, strikes_, is_today, day):
    s7 = ""
    if strikes_:
        L = strikes_["last7"]
        s7 = (f'<div class="card"><h2>Strikes, 7 days to {E(strikes_["last_day"])}</h2><p>{n(L["launched"])} drones and missiles launched '
              f'({n(L["drones_launched"])} drones, {n(L["missiles_launched"])} missiles); {n(L["destroyed"])} reported shot down or suppressed'
              f'{f" ({L["rate"]}%)" if L.get("rate") is not None else ""}. <a href="{pre}strikes/">Strike charts</a>.</p></div>')
    iswh = (f'<div class="card"><h2>ISW assessment</h2><p><a href="{E(isw_["url"])}" rel="noopener" target="_blank">{E(isw_["title"])}</a></p></div>' if isw_ else "")
    h1 = f"Ukraine war daily brief — {day_h}" if is_today else f"Ukraine war update {day_h}"
    lede = ("Today's Ukraine war daily brief groups headlines from Kyiv Independent, Ukrinform and Ukrainska Pravda, then adds the latest ISW assessment and Air Force strike totals. It is regenerated every six hours and is not edited by a human."
            if is_today else
            f"Archived Ukraine war update for {E(day_h)}. This page keeps that day's automated brief: headline themes, the ISW assessment link, and strike totals. It does not track units or movements.")
    return f'''<main class="wrap">
  <p class="crumbs"><a href="{pre}">{NAME}</a> · <a href="{pre}brief/">Daily briefs</a> · {E(day_h)}</p>
  <p class="eyebrow page-kicker">{"Updated " + E(UPDATED) if is_today else "Archived snapshot"} · Automated digest</p>
  <h1>{E(h1)}</h1>
  <p class="lede">{lede}</p>
  {DISCLAIMER}
  {brief_links(pre, day, is_today)}
  <section class="status-block"><h2>What the headlines covered</h2><div class="card">{digest_html(digest, pre)}</div>{iswh}{s7}
  <div class="card"><h2>Headlines</h2>{heads_html(top)}</div></section>
  <h2>More on the war today</h2>
  {brief_links(pre, day, is_today)}
  <p><a href="{pre}">Ukraine war update today</a> · <a href="{pre}brief/">All daily briefs</a></p>
</main>'''
bdesc = brief_desc(snap.get("digest"), TODAY_H, archived=False)
b_headline = f"Ukraine war daily brief — {TODAY_H}"
d_ld = {"@context": "https://schema.org", "@graph": [news_ld("daily-brief/", b_headline, bdesc, UPDATED_ISO, UPDATED_ISO),
        crumbs_ld([(NAME, SITE + "/"), ("Ukraine war daily brief", f"{SITE}/daily-brief/")])]}
(OUTD / "daily-brief").mkdir(parents=True, exist_ok=True)
(OUTD / "daily-brief/index.html").write_text(page("daily-brief/", f"{b_headline} | {NAME}", bdesc,
    brief_body("../", TODAY_H, snap.get("digest"), snap.get("top", []), isw, st, True, TODAY), d_ld, og_type="article",
    published=UPDATED_ISO, modified=UPDATED_ISO), encoding="utf-8")
brief_paths = []
for a in archive:
    day = a["day"]; dh = pretty_day(day); path = f"brief/{day}/"
    headline = f"Ukraine war update {dh}"
    desc = brief_desc(a.get("digest"), dh, archived=True)
    published = a.get("generated") or (day + "T00:00:00+00:00")
    ld = {"@context": "https://schema.org", "@graph": [news_ld(path, headline, desc, published, published),
          crumbs_ld([(NAME, SITE + "/"), ("Daily briefs", f"{SITE}/brief/"), (dh, f"{SITE}/{path}")])]}
    (OUTD / path).mkdir(parents=True, exist_ok=True)
    (OUTD / path / "index.html").write_text(page(path, f"{headline} | {NAME}", desc,
        brief_body("../../", dh, a.get("digest"), a.get("top", []), a.get("isw"), a.get("strikes"), False, day), ld,
        og_type="article", published=published, modified=published), encoding="utf-8")
    brief_paths.append((path, day, headline, published, desc))
lis = "".join(f'<li><a href="{d}/"><time datetime="{d}">{E(pretty_day(d))}</time> — Ukraine war update</a></li>' for _, d, *_ in brief_paths)
arch_title = f"Ukraine war daily brief archive | {NAME}"
arch_desc = "Archive of Frontlineradar Ukraine war daily briefs, one automated update per UTC day, with links to the front line map and strike charts."
(OUTD / "brief").mkdir(parents=True, exist_ok=True)
(OUTD / "brief/index.html").write_text(page("brief/", arch_title, arch_desc,
    f'<main class="wrap"><p class="crumbs"><a href="../">{NAME}</a> · Daily brief archive</p>'
    f'<h1>Ukraine war daily brief archive</h1>'
    f'<p class="lede">One automated Ukraine war update per UTC day. The <a href="../daily-brief/">current daily brief</a> is rewritten every six hours. Older pages stay as published.</p>'
    f'<nav class="related" aria-label="Related pages"><a href="../front-line-map/">Ukraine front line map</a><a href="../strikes/">Drone and missile strikes</a><a href="../daily-brief/">Today’s brief</a></nav>'
    f'<h2>All briefs</h2><div class="card"><ul class="archive-list">{lis or "<li>No archived briefs yet.</li>"}</ul></div>'
    f'<h2>What a brief contains</h2><p class="lede">Each brief groups public headlines by topic, links the latest Institute for the Study of War assessment, and quotes weekly drone and missile totals. It never lists unit locations or movements.</p></main>',
    {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": "Ukraine war daily brief archive", "url": f"{SITE}/brief/", "description": arch_desc, "isPartOf": {"@id": SITE + "/#site"}},
        crumbs_ld([(NAME, SITE + "/"), ("Daily briefs", f"{SITE}/brief/")])]}), encoding="utf-8")

# ------------------------------------------------------------------ strikes page
s_title = f"Ukraine drone and missile strikes | {NAME}"
s_desc = clip("Russian drone and missile strikes on Ukraine, charted from Ukrainian Air Force reports. "
              + (f"Last 7 days to {st['last_day']}: {st['last7']['launched']:,} launched, {st['last7']['rate']}% reported downed." if st else "Daily and weekly totals only."))
s_ld = {"@context": "https://schema.org", "@graph": [
    {"@type": "Dataset", "name": "Russian drone and missile launches at Ukraine — daily and weekly totals", "description": s_desc, "url": f"{SITE}/strikes/",
     "license": "https://creativecommons.org/licenses/by-nc-sa/4.0/", "dateModified": UPDATED_ISO, "creator": ORG,
     "isBasedOn": "https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine",
     **({"temporalCoverage": f"{st['first_day']}/{st['last_day']}"} if st else {})},
    crumbs_ld([(NAME, SITE + "/"), ("Drone and missile attacks", f"{SITE}/strikes/")])]}
peak = f'<p>Largest single reported day in the dataset: <b>{n(st["peak"]["launched"])}</b> drones and missiles on {E(st["peak"]["date"])}.</p>' if st else ""
(OUTD / "strikes").mkdir(parents=True, exist_ok=True)
(OUTD / "strikes/index.html").write_text(page("strikes/", s_title, s_desc, f'''<main class="wrap">
  <p class="crumbs"><a href="../">{NAME}</a> · Drone and missile attacks</p>
  <p class="eyebrow page-kicker">Updated {E(UPDATED)}</p>
  <h1>Ukraine drone and missile strikes</h1>
  <p class="lede">Daily and weekly totals of Russian drones (Shahed/Geran and others) and missiles launched at Ukraine, and the number Ukraine’s Air Force reported shot down or suppressed.</p>
  {metrics_html("../")}
  {DISCLAIMER}
  <section>{strikes_section("../", full=True)}{peak}</section>
  <h2>How these strike numbers are counted</h2>
  <p class="lede">Each bar is a sum of launches and reported interceptions for that day or week. The figures come from Petro Ivaniuk’s dataset of Ukrainian Air Force statements, shared here as totals only under CC BY-NC-SA 4.0. They are claims, they can be revised, and they are not a map of where anything struck. For the area-level control view, see the <a href="../front-line-map/">Ukraine front line map</a>, or read the <a href="../daily-brief/">Ukraine war daily brief</a>.</p>
</main>''', s_ld, extra_head=CHART), encoding="utf-8")

# ------------------------------------------------------------------ map page
m_as = ""
if ctrl.get("as_of"):
    try: m_as = pretty_day(ctrl["as_of"])
    except Exception: m_as = ctrl["as_of"]
m_title = f"Ukraine front line map | {NAME}"
m_desc = clip("Ukraine war map today: assessed Ukrainian-controlled, contested and Russian-controlled areas"
              + (f" as of {m_as}" if m_as else "")
              + ". Area-level and delayed, from VIINA 2.0 (ODbL). Not a live front line or unit map.")
MAP_FAQ = [
    ("Is this a live Ukraine war map?", "No. This Ukraine front line map is area-level and delayed by days. It does not show military units, troop movements, or a live front line."),
    ("What does the Ukraine front line map show?", "It shows three assessed areas: Ukrainian-controlled, contested, and Russian-controlled. Populated-place statuses are merged into those areas and then simplified. Boundaries are approximate."),
    ("Where does the Ukraine control data come from?", "VIINA 2.0 by Yuri Zhukov and Natalie Ayers, shared under the Open Database License (ODbL). The simplified GeoJSON on this page is published under the ODbL as well."),
]
m_faq_html = "".join(f"<h3>{E(q)}</h3><p>{E(a)}</p>" for q, a in MAP_FAQ)
m_ld = {"@context": "https://schema.org", "@graph": [
    {"@type": "Map", "name": "Ukraine front line map", "description": m_desc, "url": f"{SITE}/front-line-map/",
     "license": ODBL, "isBasedOn": VIINA, "dateModified": UPDATED_ISO,
     "spatial": "https://github.com/zhukovyuri/VIINA",
     "creator": {"@id": SITE + "/#org"}},
    {"@type": "Dataset", "name": "Ukraine territorial control, derived from VIINA 2.0",
     "description": m_desc, "url": f"{SITE}/assets/control.geojson", "license": ODBL,
     "creator": ORG, "isBasedOn": VIINA,
     "citation": "Zhukov, Yuri and Natalie Ayers. VIINA 2.0. Open Database License (ODbL).",
     **({"temporalCoverage": ctrl["as_of"]} if ctrl.get("as_of") else {})},
    {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in MAP_FAQ]},
    crumbs_ld([(NAME, SITE + "/"), ("Ukraine front line map", f"{SITE}/front-line-map/")])]}
(OUTD / "front-line-map").mkdir(parents=True, exist_ok=True)
(OUTD / "front-line-map/index.html").write_text(page("front-line-map/", m_title, m_desc, f'''<main class="wrap">
  <p class="crumbs"><a href="../">{NAME}</a> · Ukraine front line map</p>
  <h1>Ukraine front line map</h1>
  <p class="lede">An area-level Ukraine war map of assessed control. It is delayed and approximate, and it is not a picture of where units are.</p>
  {DISCLAIMER}
  <section>{map_section("../")}</section>
  <h2>What this map shows</h2>
  <p class="lede">Light blue is assessed as Ukrainian-controlled, amber as contested, and red as Russian-controlled. The shapes are populated-place cells that share a status, dissolved together and simplified so the file stays small. A pocket of contested ground can be only a few places, so it may look small next to the rest of the country.</p>
  <h2>How the map is made</h2>
  <p class="lede">Each build reads the latest VIINA 2.0 control table, keeps that day’s status for every populated place, and joins it to the VIINA tessellation. VIINA 2.0 (Zhukov &amp; Ayers) is available under the <a href="{ODBL}">Open Database License (ODbL)</a>. The derived <a href="../assets/control.geojson">control.geojson</a> is published under the ODbL as well. If the download fails, the previous layer stays up. Nothing here is a movement arrow or a unit location.</p>
  <nav class="related" aria-label="Related pages"><a href="../daily-brief/">Ukraine war daily brief</a><a href="../strikes/">Drone and missile strikes</a><a href="../brief/">Brief archive</a></nav>
  <section id="faq"><h2>Front line map FAQ</h2><div class="card" id="faq-list">{m_faq_html}</div></section>
</main>''', m_ld, extra_head=LEAFLET if map_ready() else ""), encoding="utf-8")

# ------------------------------------------------------------------ data.js, sitemap, robots, CNAME
src_geo = ROOT / "out/control.geojson"
if src_geo.exists():
    shutil.copyfile(src_geo, OUTD / "assets/control.geojson")
data = {"updated": UPDATED, "strikes": ({"daily": st["daily90"], "weekly": st["weekly"]} if st else None)}
(OUTD / "assets/data.js").write_text("window.FR_DATA=" + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
pages = [
    ("", "1.0", "hourly", TODAY),
    ("daily-brief/", "0.9", "hourly", TODAY),
    ("strikes/", "0.8", "daily", TODAY),
    ("front-line-map/", "0.9", "daily", (ctrl.get("as_of") or TODAY)[:10]),
    ("brief/", "0.6", "daily", TODAY),
]
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u, pr, cf, last in pages:
    sm.append(f"  <url><loc>{SITE}/{u}</loc><lastmod>{xml_esc(last)}</lastmod><changefreq>{cf}</changefreq><priority>{pr}</priority></url>")
for p, d, _headline, published, _desc in brief_paths:
    last = (published or d)[:10]
    sm.append(f"  <url><loc>{SITE}/{p}</loc><lastmod>{xml_esc(last)}</lastmod><changefreq>{"daily" if d == TODAY else "never"}</changefreq><priority>0.7</priority></url>")
sm.append("</urlset>\n")
(OUTD / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")
news_items = []
for p, d, headline, published, _desc in brief_paths:
    try: age = (GEN.date() - dt.date.fromisoformat(d)).days
    except Exception: continue
    if age < 0 or age > 1: continue
    pub = published if "T" in str(published) else f"{d}T00:00:00+00:00"
    news_items.append(f"""  <url>
    <loc>{SITE}/{p}</loc>
    <news:news>
      <news:publication>
        <news:name>{xml_esc(NAME)}</news:name>
        <news:language>en</news:language>
      </news:publication>
      <news:publication_date>{xml_esc(pub)}</news:publication_date>
      <news:title>{xml_esc(headline)}</news:title>
    </news:news>
  </url>""")
news_sm = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
           *news_items, "</urlset>\n"]
(OUTD / "news-sitemap.xml").write_text("\n".join(news_sm), encoding="utf-8")
(OUTD / "robots.txt").write_text(
    "User-agent: *\nAllow: /\n\n"
    f"Sitemap: {SITE}/sitemap.xml\n"
    f"Sitemap: {SITE}/news-sitemap.xml\n", encoding="utf-8")
rss_items = []
for p, d, headline, published, desc in brief_paths:
    try: pub_dt = dt.datetime.fromisoformat(published)
    except Exception: pub_dt = dt.datetime.fromisoformat(d + "T00:00:00+00:00")
    link = f"{SITE}/{p}"
    rss_items.append(
        f"<item><title>{xml_esc(headline)}</title><link>{link}</link>"
        f"<guid isPermaLink=\"true\">{link}</guid><pubDate>{xml_esc(format_datetime(pub_dt))}</pubDate>"
        f"<description>{xml_esc(desc)}</description></item>")
(OUTD / "feed.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<rss version="2.0"><channel>'
    f"<title>{xml_esc(NAME)} — Ukraine war daily briefs</title>"
    f"<link>{SITE}/brief/</link>"
    f"<description>Automated Ukraine war updates: daily briefs with headlines, the ISW assessment and strike totals. No unit locations.</description>"
    "<language>en</language>"
    f"<lastBuildDate>{xml_esc(format_datetime(GEN))}</lastBuildDate>"
    + "".join(rss_items) + "</channel></rss>\n", encoding="utf-8")
manifest = {"name": NAME, "short_name": NAME,
            "description": "Ukraine war update today: daily brief, front line map and strike charts.",
            "start_url": "/", "scope": "/", "display": "standalone", "lang": "en",
            "background_color": "#0b0e14", "theme_color": "#0b0e14",
            "icons": [{"src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}]}
(OUTD / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(OUTD / "CNAME").write_text("frontlineradar.org\n", encoding="utf-8")
print("built site/ updated", UPDATED, "| briefs archived:", len(brief_paths), "| news urls:", len(news_items), "| strikes:", "yes" if st else "no")
