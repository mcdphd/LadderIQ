"""LadderIQ Phase 1 shadow Northeast weather-sentiment observer.

Research-only hypothesis: cloudier/wetter conditions around major Northeast financial
centers may correlate with weaker risk appetite. This module NEVER changes OPS,
recommendations, ladders, eligibility, or capital allocation.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HISTORY_FILE = "weather_sentiment_history.json"
NY = ZoneInfo("America/New_York")
CITIES = {
    "New York": (40.7128, -74.0060),
    "Philadelphia": (39.9526, -75.1652),
    "Boston": (42.3601, -71.0589),
}


def _next_weekday(d):
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _target_session_date(now=None):
    now = now or datetime.now(NY)
    d = now.date()
    # Nightly LadderIQ runs are intended to inform the next market session.
    if d.weekday() >= 5 or now.hour >= 16:
        d += timedelta(days=1)
    return _next_weekday(d)


def _fetch_city(name, lat, lon, target_date):
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "hourly": "cloud_cover,precipitation_probability,precipitation",
        "timezone": "America/New_York",
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
    })
    req = urllib.request.Request(
        "https://api.open-meteo.com/v1/forecast?" + params,
        headers={"User-Agent": "LadderIQ/1.0 shadow-weather-research"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.load(resp)
    h = payload.get("hourly") or {}
    times = h.get("time") or []
    cloud = h.get("cloud_cover") or []
    pop = h.get("precipitation_probability") or []
    precip = h.get("precipitation") or []
    rows = []
    for i, ts in enumerate(times):
        try:
            hour = int(ts[11:13])
        except Exception:
            continue
        if 9 <= hour <= 16:
            rows.append((float(cloud[i] or 0), float(pop[i] or 0), float(precip[i] or 0)))
    if not rows:
        raise ValueError(f"No market-hours weather rows returned for {name}")
    avg_cloud = sum(r[0] for r in rows) / len(rows)
    avg_pop = sum(r[1] for r in rows) / len(rows)
    precip_mm = sum(r[2] for r in rows)
    rainy_hours = sum(1 for r in rows if r[2] > 0)
    # Intentionally simple and auditable during shadow evaluation.
    score = max(0.0, min(100.0, 100.0 - 0.70 * avg_cloud - 0.30 * avg_pop))
    return {
        "city": name,
        "score": round(score, 1),
        "avg_cloud_cover_pct": round(avg_cloud, 1),
        "avg_precip_probability_pct": round(avg_pop, 1),
        "forecast_precip_mm": round(precip_mm, 2),
        "forecast_rainy_market_hours": rainy_hours,
    }


def _load_history(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def calculate_shadow_weather(root):
    root = Path(root)
    target = _target_session_date()
    cities, errors = [], []
    for name, (lat, lon) in CITIES.items():
        try:
            cities.append(_fetch_city(name, lat, lon, target))
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if cities:
        score = round(sum(c["score"] for c in cities) / len(cities), 1)
        avg_cloud = round(sum(c["avg_cloud_cover_pct"] for c in cities) / len(cities), 1)
        avg_pop = round(sum(c["avg_precip_probability_pct"] for c in cities) / len(cities), 1)
        precip_mm = round(sum(c["forecast_precip_mm"] for c in cities), 2)
        if score >= 70:
            signal = "Favorable"
        elif score >= 45:
            signal = "Neutral"
        else:
            signal = "Unfavorable"
        status = "ok"
    else:
        score, avg_cloud, avg_pop, precip_mm = None, None, None, None
        signal, status = "Unavailable", "error"

    result = {
        "score": score,
        "signal": signal,
        "target_session_date": target.isoformat(),
        "avg_cloud_cover_pct": avg_cloud,
        "avg_precip_probability_pct": avg_pop,
        "forecast_precip_mm_total": precip_mm,
        "cities": cities,
        "errors": errors,
        "status": status,
        "shadow_only": True,
        "affects_live_ladders": False,
        "hypothesis": "Northeast cloud/rain conditions may correlate with market risk appetite; research only.",
        "source": "Open-Meteo forecast API",
        "checked_at": datetime.now(NY).isoformat(timespec="seconds"),
    }

    history_path = root / HISTORY_FILE
    history = _load_history(history_path)
    # One latest forecast observation per target session; reruns replace that session's row.
    history = [x for x in history if x.get("target_session_date") != result["target_session_date"]]
    history.append(result)
    history = history[-400:]
    try:
        history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except Exception:
        pass
    return result
