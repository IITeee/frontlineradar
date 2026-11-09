"""Territorial control — STUB.

No DeepStateMap or ISW geodata is ingested yet: both require permission before
their map layers can be reused. This module defines the interface that
refresh.py calls so a licensed GeoJSON source can be plugged in later without
touching the rest of the pipeline.

To enable later:
  1. Get written permission / API access (e.g. DeepStateMap API, or another
     source whose licence allows redistribution of derived statistics).
  2. Set CONTROL_GEOJSON_URL (and CONTROL_SOURCE_NAME / CONTROL_SOURCE_URL)
     as repository secrets or variables and expose them in pages.yml.
  3. Implement `summarise()` below: polygons of occupied territory ->
     total km² and per-oblast share (needs oblast boundaries, e.g. geoBoundaries
     ADM1 for Ukraine, CC BY 4.0) and the day-over-day change.

Contract — `load(prev)` returns a dict that is stored as snapshot["control"]:
  {
    "available": bool,           # False => site shows the placeholder
    "source": str, "source_url": str, "as_of": "YYYY-MM-DD",
    "occupied_km2": float,       # total area under Russian control
    "change_km2_24h": float,     # vs previous snapshot
    "oblasts": [ {"name": str, "occupied_pct": float, "change_km2": float}, ... ],
    "note": str
  }
The site never renders unit positions or movements, only aggregated area.
"""
import os

def load(prev=None):
    url = os.environ.get("CONTROL_GEOJSON_URL", "").strip()
    if not url:
        return {"available": False,
                "note": "Territorial-control statistics are pending data permission. "
                        "See DeepStateMap and ISW for current maps."}
    # TODO: fetch GeoJSON from `url`, then call summarise(). Kept unimplemented
    # on purpose until a source with redistribution rights is confirmed.
    return {"available": False,
            "note": "CONTROL_GEOJSON_URL is set but the ingestion step is not implemented yet."}

def summarise(geojson, oblast_boundaries, prev=None):
    """TODO: return the dict described in the module docstring."""
    raise NotImplementedError
