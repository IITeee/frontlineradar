# Frontlineradar

A static, English daily **radar of the war in Ukraine** for [frontlineradar.org](https://frontlineradar.org). Sister project of [Pandemicradar](https://github.com/IITeee/pandemicradar), same structure: `refresh.py` → `out/snapshot.json`, `build_site.py` → `site/`, GitHub Actions deploys `site/` to GitHub Pages.

**Safety rule:** the site never publishes unit locations, troop movements or anything real-time that could help target people. It aggregates official statistics after the fact and links to published reporting.

## What is on the site

| Section | Source | Status |
|---|---|---|
| Daily brief (automated digest + top headlines) | Kyiv Independent, Ukrinform, Ukrainska Pravda RSS — titles and links only | live |
| UK MoD (Ukraine-related) | GOV.UK Atom feed, Ministry of Defence, keyword `ukraine` | live |
| Latest ISW assessment (link) | understandingwar.org feed; falls back to Google News RSS because ISW returns 403 to bots | live |
| Drone & missile strikes chart | Petro Ivaniuk, [Massive Missile Attacks on Ukraine](https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine) (Kaggle, CC BY-NC-SA 4.0) — daily/weekly sums only | live |
| Territorial control map | VIINA 2.0 (Zhukov & Ayers), [ODbL](https://opendatacommons.org/licenses/odbl/1-0/) — dissolved populated-place status, not units | live |
| Air-raid alerts | `alerts.py` → alerts.in.ua, needs `ALERTS_IN_UA_TOKEN` | hidden until token is set |
| Newsletter | `SIGNUP_ENDPOINT` in `site/assets/app.js` | “Coming soon” |
| Comments | Giscus, `GISCUS` block in `site/assets/app.js` | TODO: repoId / categoryId |
| Analytics | GoatCounter, site code `frontlineradar` | TODO: commented out in `build_site.py` |

Pages: `/`, `/daily-brief/`, `/brief/` (archive) + `/brief/YYYY-MM-DD/`, `/strikes/`, `/front-line-map/`.

SEO: title/description/canonical per page, Open Graph + Twitter card (`site/assets/og.png`, regenerate with `python3 tools/make_og.py`, needs Pillow), JSON-LD (WebSite, Organization, NewsArticle, FAQPage, Dataset, BreadcrumbList), FAQ, `robots.txt` and `sitemap.xml` regenerated on every build, `CNAME`, `favicon.svg`.

## Run locally

```bash
pip install -r requirements.txt   # Shapely, for the control map
python3 refresh.py && python3 build_site.py
python3 -m http.server -d site 8000
```

Python 3.12+. Feeds and the strike chart use the standard library. The control map also needs Shapely. Each source is independent: if one fails, its previous value from `out/snapshot.json` is kept and the failure is shown under “Source status” on the site. A failed VIINA download keeps the last derived `out/control.geojson`.

## Deploy

[`.github/workflows/pages.yml`](.github/workflows/pages.yml) runs every 6 hours, on push to `main` and on manual dispatch. It refreshes, builds, commits `out/` and `site/` back with `[skip ci]`, and deploys `site/` to Pages.

One-time setup after creating the GitHub repo:

1. **Settings → Pages → Source: GitHub Actions**, custom domain `frontlineradar.org`, then **Enforce HTTPS**.
2. DNS at the registrar (apex): `A` 185.199.108.153 / .109.153 / .110.153 / .111.153, `AAAA` 2606:50c0:8000::153 / 8001 / 8002 / 8003, and `www` `CNAME` → `<user>.github.io`.
3. Optional secret `ALERTS_IN_UA_TOKEN` (alerts.in.ua). The control map downloads VIINA on its own; raw files are cached by Actions and are not committed.
4. Enable Discussions + install the Giscus app, fill `repoId`/`categoryId` in `site/assets/app.js`.
5. Create the GoatCounter site `frontlineradar` and uncomment the script at the bottom of the page template in `build_site.py`.

## Licences and attribution

- Strike totals are derived from Petro Ivaniuk's dataset (CC BY-NC-SA 4.0) and are shared under the same licence; the site is non-commercial. Raw CSVs are not committed.
- Headlines belong to their publishers; only titles and links are shown.
- Territorial control: VIINA 2.0 (Zhukov & Ayers), https://github.com/zhukovyuri/VIINA — contains information from VIINA, made available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/1-0/). The derived `control.geojson` (dissolved and simplified areas) is published under the ODbL as well. Raw VIINA downloads are not committed.
