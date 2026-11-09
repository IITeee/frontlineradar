"""Frontlineradar: renders site/ from out/snapshot.json and out/archive/*.json.

Writes site/index.html, /daily-brief/, /strikes/, /front-line-map/, /brief/YYYY-MM-DD/,
site/assets/data.js, site/sitemap.xml, site/robots.txt and site/CNAME.
"""
import json, re, html, pathlib, datetime as dt

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
    ("Who controls which areas of Ukraine?", "For current front-line maps, see DeepStateMap and the ISW interactive map, which are linked on the Front-line map page. Frontlineradar will add area statistics per oblast once a data source with reuse permission is in place."),
    ("How is the daily brief written?", "The daily brief is an automated digest. It groups the latest headlines by keyword into topics such as strikes, front line, energy and diplomacy, and adds the weekly strike numbers. It is not edited by a human and links to the original articles."),
    ("How often is the site updated?", "Every six hours. Each page shows the time of the latest snapshot in UTC."),
]

# ------------------------------------------------------------------ layout
NAV = [("Brief", "daily-brief/"), ("Strikes", "strikes/"), ("Map", "front-line-map/"), ("FAQ", "#faq"), ("Sources", "#method")]
def page(path, title, desc, body, ld, og_type="website", extra_head=""):
    depth = path.count("/")
    pre = "../" * depth
    canon = f"{SITE}/{path}"
    nav = "".join(f'<a href="{(pre if not h.startswith("#") else pre if depth else "") + h}">{E(t)}</a>' for t, h in NAV)
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
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="{pre}assets/style.css">
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
<nav class="foot-links" aria-label="Site pages"><a href="{pre or './'}">Home</a><a href="{pre}daily-brief/">Daily brief</a><a href="{pre}strikes/">Drone &amp; missile strikes</a><a href="{pre}front-line-map/">Front-line map</a><a href="{pre}brief/">Archive</a></nav>
<p>Strike statistics: Petro Ivaniuk, “Massive Missile Attacks on Ukraine” (CC BY-NC-SA 4.0); derived totals on this site are shared under the same licence. Headlines link to and belong to their publishers.</p>
<p>Privacy-friendly, cookie-free analytics by GoatCounter.</p>
</div></footer>
<script src="{pre}assets/data.js"></script>
<script src="{pre}assets/app.js"></script>
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

MAP_LINKS = [("DeepStateMap", "https://deepstatemap.live/en", "Ukrainian OSINT map of the front line, updated daily."),
             ("ISW interactive map", "https://storymaps.arcgis.com/stories/36a7f6a6f5a9448496de641cf64bd375", "Institute for the Study of War and AEI Critical Threats map of Russia’s invasion of Ukraine."),
             ("ISW Russia–Ukraine research", "https://understandingwar.org/research/russia-ukraine/", "Daily campaign assessments with assessed control and advances.")]
def map_section(pre=""):
    if ctrl.get("available"):
        rows = "".join(f'<tr><td>{E(o["name"])}</td><td class="num">{o["occupied_pct"]:.1f}%</td><td class="num">{o.get("change_km2",0):+,.0f} km²</td></tr>' for o in ctrl.get("oblasts", []))
        return (f'<div class="card"><p>Occupied area: <b>{n(round(ctrl["occupied_km2"]))} km²</b> ({ctrl.get("change_km2_24h",0):+,.0f} km² in 24 h). '
                f'Source: <a href="{E(ctrl["source_url"])}">{E(ctrl["source"])}</a>, as of {E(ctrl["as_of"])}.</p>'
                f'<div class="table-wrap"><table><thead><tr><th>Oblast</th><th>Occupied</th><th>Change</th></tr></thead><tbody>{rows}</tbody></table></div></div>')
    links = "".join(f'<a href="{E(u)}" target="_blank" rel="noopener">{E(t)} ↗</a>' for t, u, _ in MAP_LINKS)
    return (f'<div class="card"><div class="placeholder"><div class="ph-map" aria-hidden="true"></div>'
            f'<p><b>Control map and per-oblast statistics are coming.</b> We are waiting for permission to reuse a front-line dataset. Until then, see the maps maintained by these sources:</p>'
            f'<div class="linkbtns">{links}</div></div></div>')

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
    return {"@type": "NewsArticle", "headline": headline[:110], "description": desc, "datePublished": published, "dateModified": modified,
            "inLanguage": "en", "mainEntityOfPage": f"{SITE}/{path}", "isAccessibleForFree": True, "image": [f"{SITE}/assets/og.png"],
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
brief_title = f"Ukraine war daily brief — {TODAY_H}"
home_title = "Frontlineradar — Ukraine war daily radar: front line, drone & missile attacks"
home_desc = ("Daily radar of the war in Ukraine: latest headlines, the newest ISW assessment and charts of Russian drone and missile "
             "attacks vs. interceptions. OSINT and official sources, attributed and delayed — no live military positions.")
faq_html = "".join(f"<h3>{E(q)}</h3><p>{E(a)}</p>" for q, a in FAQ)
status_html = "".join(f'<span class="chip" style="color:{"var(--low)" if v=="ok" else "var(--mid)" if v.startswith("stub") else "var(--high)"}">● {E(k)}: {E(v)}</span>' for k, v in snap["status"].items())
SOURCES = [("Kyiv Independent", "https://kyivindependent.com/", "Headlines via RSS (titles and links only)"),
           ("Ukrinform", "https://www.ukrinform.net/", "Ukraine's national news agency, headlines via RSS"),
           ("Ukrainska Pravda", "https://www.pravda.com.ua/eng/", "Headlines via RSS"),
           ("UK Ministry of Defence (GOV.UK)", "https://www.gov.uk/government/organisations/ministry-of-defence", "Ukraine-related MoD news via the GOV.UK Atom feed. Defence Intelligence updates are published on X (@DefenceHQ)."),
           ("Institute for the Study of War", "https://understandingwar.org/research/russia-ukraine/", "Link to the latest Russian Offensive Campaign Assessment"),
           ("Massive Missile Attacks on Ukraine", "https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine", "Petro Ivaniuk, from Ukrainian Air Force reports, CC BY-NC-SA 4.0"),
           ("DeepStateMap", "https://deepstatemap.live/en", "Front-line map (linked, not embedded)")]
src_html = "".join(f'<li><a href="{E(u)}" target="_blank" rel="noopener">{E(t)}</a><small>{E(d)}</small></li>' for t, u, d in SOURCES)
home_ld = {"@context": "https://schema.org", "@graph": [
    {"@type": "WebSite", "@id": SITE + "/#site", "name": NAME, "url": SITE + "/", "description": home_desc, "inLanguage": "en", "publisher": {"@id": SITE + "/#org"}},
    ORG,
    news_ld("daily-brief/", brief_title, "Automated digest of today's Ukraine war headlines, ISW assessment and drone and missile strike statistics.", first_today, UPDATED_ISO),
    {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}]}
home_body = f'''<section class="hero" id="top"><div class="wrap">
  <p class="eyebrow">Ukraine war radar · Updated <span id="updated-static">{E(UPDATED)}</span></p>
  <h1>The war in Ukraine, <span class="grad">every day</span></h1>
  <p class="lede">Headlines from Ukrainian and international outlets, the latest ISW assessment, and Russian drone and missile attacks charted from Ukrainian Air Force reports.</p>
  {metrics_html()}
  {DISCLAIMER}
</div></section>
<main class="wrap">
  <section id="brief"><div class="sec-head"><h2>Daily brief — {E(TODAY_H)}</h2><p>What the headlines of the last 36 hours are about. <a href="daily-brief/">Open the full brief</a> or browse the <a href="brief/">archive</a>.</p></div>
    <div class="grid2"><div class="card">{digest_html(snap.get("digest"))}</div><div class="card"><h3>Top headlines</h3>{heads_html(snap.get("top", [])[:8])}</div></div>
  </section>
  <section id="isw" style="padding-top:0">{isw_html()}</section>
  <section id="strikes"><div class="sec-head"><h2>Drone and missile attacks</h2><p>Russian drones and missiles launched at Ukraine, and how many Ukraine’s Air Force reported shot down or suppressed.</p></div>{strikes_section()}</section>
  <section id="map"><div class="sec-head"><h2>Who controls what</h2><p>Front-line maps from DeepStateMap and ISW. Our own control statistics per oblast will appear here.</p></div>{map_section()}</section>
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
(OUTD / "index.html").write_text(page("", home_title, home_desc, home_body, home_ld, extra_head=CHART), encoding="utf-8")

# ------------------------------------------------------------------ daily brief (+ archive)
def brief_body(pre, day_h, digest, top, isw_, strikes_, is_today):
    s7 = ""
    if strikes_:
        L = strikes_["last7"]
        s7 = (f'<div class="card"><h3>Strikes, 7 days to {E(strikes_["last_day"])}</h3><p>{n(L["launched"])} drones and missiles launched '
              f'({n(L["drones_launched"])} drones, {n(L["missiles_launched"])} missiles); {n(L["destroyed"])} reported shot down or suppressed'
              f'{f" ({L["rate"]}%)" if L.get("rate") is not None else ""}. <a href="{pre}strikes/">Charts</a>.</p></div>')
    iswh = (f'<div class="card"><h3>ISW assessment</h3><p><a href="{E(isw_["url"])}" target="_blank" rel="noopener">{E(isw_["title"])}</a></p></div>' if isw_ else "")
    return f'''<main class="wrap">
  <p class="crumbs"><a href="{pre}">{NAME}</a> · <a href="{pre}brief/">Daily brief</a> · {E(day_h)}</p>
  <p class="eyebrow page-kicker">Automated digest · {"Updated " + E(UPDATED) if is_today else "Archived snapshot"}</p>
  <h1>Ukraine war daily brief — {E(day_h)}</h1>
  <p class="lede">An automated summary of the day's headlines from Kyiv Independent, Ukrinform and Ukrainska Pravda, with the latest ISW assessment and Air Force strike figures.</p>
  {DISCLAIMER}
  <section class="status-block"><div class="card">{digest_html(digest, pre)}</div>{iswh}{s7}
  <div class="card"><h3>Headlines</h3>{heads_html(top)}</div></section>
  <p><a href="{pre}">Back to the Frontlineradar dashboard</a> · <a href="{pre}brief/">All daily briefs</a></p>
</main>'''
bdesc = (snap["digest"][0]["text"] + " " if snap.get("digest") else "") + "Automated daily digest of Ukraine war headlines, the ISW assessment and drone and missile strike data."
d_ld = {"@context": "https://schema.org", "@graph": [news_ld("daily-brief/", brief_title, bdesc, first_today, UPDATED_ISO),
        crumbs_ld([(NAME, SITE + "/"), ("Daily brief", f"{SITE}/daily-brief/")])]}
(OUTD / "daily-brief").mkdir(parents=True, exist_ok=True)
(OUTD / "daily-brief/index.html").write_text(page("daily-brief/", f"{brief_title} | {NAME}", bdesc,
    brief_body("../", TODAY_H, snap.get("digest"), snap.get("top", []), isw, st, True), d_ld, og_type="article"), encoding="utf-8")
brief_paths = []
for a in archive:
    day = a["day"]; dh = pretty_day(day); path = f"brief/{day}/"
    t = f"Ukraine war daily brief — {dh}"
    desc = (a["digest"][0]["text"] + " " if a.get("digest") else "") + f"Archived Frontlineradar digest for {dh}."
    ld = {"@context": "https://schema.org", "@graph": [news_ld(path, t, desc, day + "T00:00:00+00:00", a["generated"]),
          crumbs_ld([(NAME, SITE + "/"), ("Daily brief", f"{SITE}/brief/"), (dh, f"{SITE}/{path}")])]}
    (OUTD / path).mkdir(parents=True, exist_ok=True)
    (OUTD / path / "index.html").write_text(page(path, f"{t} | {NAME}", desc,
        brief_body("../../", dh, a.get("digest"), a.get("top", []), a.get("isw"), a.get("strikes"), False), ld, og_type="article"), encoding="utf-8")
    brief_paths.append((path, day))
lis = "".join(f'<li><a href="{d}/">{E(pretty_day(d))}</a></li>' for _, d in brief_paths)
(OUTD / "brief").mkdir(parents=True, exist_ok=True)
(OUTD / "brief/index.html").write_text(page("brief/", f"Ukraine war daily briefs — archive | {NAME}", "Archive of Frontlineradar's automated daily briefs on the war in Ukraine.",
    f'<main class="wrap"><p class="crumbs"><a href="../">{NAME}</a> · Daily brief archive</p><h1>Daily brief archive</h1>'
    f'<p class="lede">One automated brief per day (UTC). The <a href="../daily-brief/">current brief</a> is updated every six hours.</p>'
    f'<div class="card"><ul class="archive-list">{lis}</ul></div></main>',
    {"@context": "https://schema.org", "@graph": [{"@type": "CollectionPage", "name": "Daily brief archive", "url": f"{SITE}/brief/"}, crumbs_ld([(NAME, SITE + "/"), ("Daily brief", f"{SITE}/brief/")])]}), encoding="utf-8")

# ------------------------------------------------------------------ strikes page
s_title = f"Russian drone and missile attacks on Ukraine — daily statistics | {NAME}"
s_desc = (f"How many Shahed-type drones and missiles Russia launches at Ukraine each day and week, and how many are shot down. "
          + (f"Last 7 days to {st['last_day']}: {st['last7']['launched']:,} launched, {st['last7']['rate']}% downed." if st else ""))
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
  <h1>Russian drone and missile attacks on Ukraine</h1>
  <p class="lede">Daily and weekly totals of Russian drones (Shahed/Geran and others) and missiles launched at Ukraine, and the number Ukraine’s Air Force reported shot down or suppressed.</p>
  {metrics_html("../")}
  {DISCLAIMER}
  <section>{strikes_section("../", full=True)}{peak}</section>
</main>''', s_ld, extra_head=CHART), encoding="utf-8")

# ------------------------------------------------------------------ map page
m_title = f"Ukraine front-line map: who controls what | {NAME}"
m_desc = "Where to find up-to-date maps of the front line in Ukraine — DeepStateMap and ISW — and Frontlineradar's upcoming per-oblast control statistics."
m_list = "".join(f'<li><a href="{E(u)}" target="_blank" rel="noopener">{E(t)}</a><small>{E(d)}</small></li>' for t, u, d in MAP_LINKS)
(OUTD / "front-line-map").mkdir(parents=True, exist_ok=True)
(OUTD / "front-line-map/index.html").write_text(page("front-line-map/", m_title, m_desc, f'''<main class="wrap">
  <p class="crumbs"><a href="../">{NAME}</a> · Front-line map</p>
  <h1>Front-line map of Ukraine</h1>
  <p class="lede">Which areas Russia and Ukraine control, according to the open-source mapping projects that track it daily.</p>
  {DISCLAIMER}
  <section>{map_section("../")}<div class="card"><h3>Maps we recommend</h3><ul class="sources">{m_list}</ul>
  <p class="note">Front-line maps are estimates based on geolocated footage and official statements and lag behind events. Frontlineradar links to these maps and does not copy their data.</p></div></section>
</main>''', {"@context": "https://schema.org", "@graph": [{"@type": "WebPage", "name": m_title, "url": f"{SITE}/front-line-map/", "description": m_desc},
              crumbs_ld([(NAME, SITE + "/"), ("Front-line map", f"{SITE}/front-line-map/")])]}), encoding="utf-8")

# ------------------------------------------------------------------ data.js, sitemap, robots, CNAME
data = {"updated": UPDATED, "strikes": ({"daily": st["daily90"], "weekly": st["weekly"]} if st else None)}
(OUTD / "assets/data.js").write_text("window.FR_DATA=" + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
urls = [("", "1.0", "hourly"), ("daily-brief/", "0.9", "hourly"), ("strikes/", "0.9", "daily"), ("front-line-map/", "0.7", "weekly"), ("brief/", "0.5", "daily")]
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u, pr, cf in urls:
    sm.append(f"  <url><loc>{SITE}/{u}</loc><lastmod>{TODAY}</lastmod><changefreq>{cf}</changefreq><priority>{pr}</priority></url>")
for p, d in brief_paths:
    sm.append(f"  <url><loc>{SITE}/{p}</loc><lastmod>{d}</lastmod><changefreq>{"daily" if d == TODAY else "never"}</changefreq><priority>0.4</priority></url>")
sm.append("</urlset>\n")
(OUTD / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")
(OUTD / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
(OUTD / "CNAME").write_text("frontlineradar.org\n", encoding="utf-8")
print("built site/ updated", UPDATED, "| briefs archived:", len(brief_paths), "| strikes:", "yes" if st else "no")
