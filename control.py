"""Territorial control from VIINA 2.0 (Zhukov & Ayers), ODbL 1.0.

Downloads the daily control table and the GeoNames tessellation, keeps the
latest date's status for each populated place, and writes a dissolved,
simplified GeoJSON (Russian-controlled, contested, Ukrainian-controlled).

Raw downloads stay in the cache directory and are never committed. If a
download or dissolve fails, the last derived GeoJSON is left in place.

The output is area-level and approximate. It has no unit locations, no
movement arrows, and no place-level points.
"""
import csv, datetime as dt, hashlib, io, json, os, pathlib, urllib.error, urllib.request, zipfile

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "out"
DERIVED = OUT / "control.geojson"
CACHE = pathlib.Path(os.environ.get("VIINA_CACHE", ROOT / ".cache" / "viina"))
UA = "frontlineradar.org (static build; +https://frontlineradar.org/)"
SOURCE = "VIINA 2.0 (Zhukov & Ayers)"
SOURCE_URL = "https://github.com/zhukovyuri/VIINA"
LICENSE = "ODbL-1.0"
LICENSE_URL = "https://opendatacommons.org/licenses/odbl/1-0/"
NOTE = ("Area-level, delayed, and approximate. Populated-place cells are merged "
        "by assessed status and simplified. Not military unit locations or movements.")
# ~200 m. Keeps cell area and stays far under the 1.5 MB ship limit.
SIMPLIFY_TOL = 0.002
COORD_DIGITS = 4
STATUSES = ("UA", "RU", "CONTESTED")


def _year_urls():
    year = dt.datetime.now(dt.timezone.utc).year
    override = os.environ.get("VIINA_CONTROL_ZIP_URL", "").strip()
    if override:
        return [override]
    return [f"https://media.githubusercontent.com/media/zhukovyuri/VIINA/main/Data/control_latest_{y}.zip"
            for y in (year, year - 1)]


def _tess_urls():
    override = os.environ.get("VIINA_TESS_URL", "").strip()
    if override:
        return [override]
    # The tessellation is a normal git blob, so the LFS media host 404s.
    # Try it first (as published for LFS objects), then the raw blob.
    return [
        "https://media.githubusercontent.com/media/zhukovyuri/VIINA/main/Data/gn_UA_tess.geojson",
        "https://raw.githubusercontent.com/zhukovyuri/VIINA/main/Data/gn_UA_tess.geojson",
    ]


def _fetch(urls, dest: pathlib.Path) -> pathlib.Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    etag_path = dest.with_name(dest.name + ".etag")
    errors = []
    for url in urls:
        headers = {"User-Agent": UA}
        if dest.exists() and etag_path.exists():
            headers["If-None-Match"] = etag_path.read_text(encoding="utf-8").strip()
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                dest.write_bytes(resp.read())
                etag = resp.headers.get("ETag")
                if etag:
                    etag_path.write_text(etag.strip(), encoding="utf-8")
                elif etag_path.exists():
                    etag_path.unlink()
                return dest
        except urllib.error.HTTPError as e:
            if e.code == 304 and dest.exists():
                return dest
            errors.append(f"{url} -> HTTP {e.code}")
        except Exception as e:
            errors.append(f"{url} -> {e}")
    raise RuntimeError("VIINA download failed: " + "; ".join(errors)[:240])


def _gid(value):
    return int(float(value))


def _iso(yyyymmdd):
    s = str(yyyymmdd)
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def _fingerprint(paths):
    parts = [f"tol={SIMPLIFY_TOL};digits={COORD_DIGITS}"]
    for path in paths:
        st = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        parts.append(f"{path.name}:{st.st_size}:{digest}")
    return "|".join(parts)


def _summary_from_file():
    doc = json.loads(DERIVED.read_text(encoding="utf-8"))
    meta = doc.get("meta") or {}
    if not doc.get("features") or not meta.get("as_of"):
        raise ValueError("derived GeoJSON is missing features")
    return _public(meta)


def _public(meta, stale=False, error=None):
    out = {"available": True, "stale": bool(stale), "geojson": "control.geojson",
           "source": meta.get("source", SOURCE), "source_url": meta.get("source_url", SOURCE_URL),
           "license": meta.get("license", LICENSE), "license_url": meta.get("license_url", LICENSE_URL),
           "as_of": meta.get("as_of"), "places": meta.get("places") or {},
           "area_km2": meta.get("area_km2") or {}, "note": meta.get("note", NOTE)}
    if error:
        out["error"] = str(error)[:160]
    return out


def _fallback(prev, err):
    if DERIVED.exists():
        try:
            kept = _summary_from_file()
        except Exception:
            kept = dict(prev or {})
            kept["available"] = True
            kept["geojson"] = "control.geojson"
        kept["stale"] = True
        kept["available"] = True
        kept["error"] = str(err)[:160]
        kept["note"] = NOTE
        return kept
    return {"available": False, "stale": False,
            "note": "Territorial-control data could not be downloaded."}


def _latest_status(zip_path):
    """Latest status per geonameid. One pass over the yearly panel."""
    best = {}
    with zipfile.ZipFile(zip_path) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(name) as raw:
            for row in csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline="")):
                try:
                    gid = _gid(row["geonameid"])
                except (TypeError, ValueError, KeyError):
                    continue
                day = row.get("date") or ""
                status = (row.get("status") or "").strip().upper()
                if status not in STATUSES or not day:
                    continue
                prev = best.get(gid)
                if prev is None or day > prev[0]:
                    best[gid] = (day, status)
    if not best:
        raise ValueError("control CSV had no usable rows")
    latest = max(day for day, _ in best.values())
    chosen = {gid: status for gid, (day, status) in best.items() if day == latest}
    return latest, chosen


def _area_km2(geom):
    import math
    from shapely import affinity
    lat = geom.centroid.y * math.pi / 180.0
    scaled = affinity.scale(geom, xfact=math.cos(lat), yfact=1.0, origin=(0, 0))
    return scaled.area * (111.32 ** 2)


def _polygons_only(geom):
    from shapely import union_all
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    if geom.geom_type == "GeometryCollection":
        parts = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon") and not g.is_empty]
        if not parts:
            raise ValueError("dissolve produced no polygons")
        return union_all(parts)
    raise ValueError(f"unexpected geometry {geom.geom_type}")


def _dissolve(tess_path, status_by_id):
    import numpy as np
    from shapely import make_valid, transform, union_all
    from shapely.geometry import mapping, shape

    with tess_path.open(encoding="utf-8") as fh:
        collection = json.load(fh)
    groups = {status: [] for status in STATUSES}
    matched = {status: 0 for status in STATUSES}
    for feature in collection.get("features") or []:
        props = feature.get("properties") or {}
        try:
            gid = _gid(props.get("geonameid"))
        except (TypeError, ValueError):
            continue
        status = status_by_id.get(gid)
        if status not in groups:
            continue
        geom = shape(feature["geometry"])
        if geom.is_empty:
            continue
        groups[status].append(geom)
        matched[status] += 1
    del collection
    if sum(matched.values()) == 0:
        raise ValueError("tessellation did not match any control rows")

    features = []
    areas = {}
    for status in STATUSES:
        geoms = groups[status]
        if not geoms:
            continue
        merged = _polygons_only(union_all(geoms))
        if not merged.is_valid:
            merged = _polygons_only(make_valid(merged))
        simplified = merged.simplify(SIMPLIFY_TOL, preserve_topology=True)
        simplified = transform(simplified, lambda coords: np.round(coords, COORD_DIGITS))
        if not simplified.is_valid:
            simplified = _polygons_only(make_valid(simplified))
        areas[status] = int(round(_area_km2(simplified)))
        features.append({
            "type": "Feature",
            "properties": {
                "status": status,
                "label": {"UA": "Ukrainian-controlled", "RU": "Russian-controlled", "CONTESTED": "Contested"}[status],
            },
            "geometry": mapping(simplified),
        })
    return features, matched, areas


def _write(meta, features):
    doc = {"type": "FeatureCollection", "meta": meta, "features": features}
    payload = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    if len(payload.encode("utf-8")) > 1_500_000:
        raise ValueError("derived GeoJSON exceeds 1.5 MB")
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = DERIVED.with_suffix(".geojson.tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(DERIVED)


def load(prev=None):
    try:
        zip_path = _fetch(_year_urls(), CACHE / "control_latest.zip")
        tess_path = _fetch(_tess_urls(), CACHE / "gn_UA_tess.geojson")
        stamp = _fingerprint((zip_path, tess_path))
        stamp_path = CACHE / "source.fingerprint"
        if DERIVED.exists() and stamp_path.exists() and stamp_path.read_text(encoding="utf-8") == stamp:
            return _summary_from_file()
        latest, status_by_id = _latest_status(zip_path)
        features, places, areas = _dissolve(tess_path, status_by_id)
        meta = {"as_of": _iso(latest), "source": SOURCE, "source_url": SOURCE_URL,
                "license": LICENSE, "license_url": LICENSE_URL,
                "places": places, "area_km2": areas, "note": NOTE,
                "derived": "Dissolved and simplified from VIINA populated-place status. Also published under the ODbL."}
        _write(meta, features)
        stamp_path.write_text(stamp, encoding="utf-8")
        summary = _public(meta)
        print(f"control: {summary['as_of']} places={places} bytes={DERIVED.stat().st_size}")
        return summary
    except Exception as e:
        print(f"control: kept previous ({e})")
        return _fallback(prev, e)
