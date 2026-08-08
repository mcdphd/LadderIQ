"""LadderIQ Phase 1 shadow market-regime observer.

This module calculates and logs a market-regime score but does NOT alter OPS,
recommendations, ladder prices, ladder sizes, or capital allocation. The
hypothetical capital multiplier is recorded only for Phase 2 analysis.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

HISTORY_FILE = "market_regime_history.json"


def _clamp(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def _scalar(value, default=0.0):
    try:
        if hasattr(value, "squeeze"):
            value = value.squeeze()
        if hasattr(value, "item"):
            value = value.item()
        return float(value)
    except Exception:
        return float(default)


def _classify(score: float):
    score = float(score)
    if score >= 85:
        return "Strong Bull", 1.00
    if score >= 70:
        return "Bull", 1.00
    if score >= 55:
        return "Neutral", 0.80
    if score >= 40:
        return "Correction", 0.60
    if score >= 25:
        return "Bear", 0.35
    return "Extreme Bear", 0.20


def _load_history(root: Path):
    path = root / HISTORY_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_history(root: Path, history):
    path = root / HISTORY_FILE
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(history, indent=2), encoding="utf-8")
    tmp.replace(path)


def calculate_shadow_regime(results: list[dict], benchmark_close, sector_scores: dict, root: Path) -> dict:
    """Calculate a 0-100 shadow market-regime score.

    V1 intentionally uses data LadderIQ already collects reliably:
    QQQ trend/drawdown/volatility plus broad-universe breadth, momentum,
    leadership health, and sector participation. No live trading logic consumes
    this score in Phase 1.
    """
    valid = [r for r in (results or []) if r.get("price") and r.get("technical_score") is not None]
    n = max(1, len(valid))

    # Broad-market breadth from the same thousands-stock universe already used
    # by the opportunity scanner.
    p20 = 100.0 * sum(bool(r.get("above_20dma")) for r in valid) / n
    p50 = 100.0 * sum(bool(r.get("above_50dma")) for r in valid) / n
    p200 = 100.0 * sum(bool(r.get("above_200dma")) for r in valid) / n
    golden = 100.0 * sum(bool(r.get("sma50_above_sma200")) for r in valid) / n
    breadth_score = _clamp(0.15*p20 + 0.30*p50 + 0.40*p200 + 0.15*golden)

    # Leadership health: how much of the liquid common-stock universe still has
    # strong technical structure. 40% at TS>=75 is treated as exceptionally
    # healthy; 20% at TS>=90 is exceptionally broad elite leadership.
    pct75 = 100.0 * sum(float(r.get("technical_score") or 0) >= 75 for r in valid) / n
    pct90 = 100.0 * sum(float(r.get("technical_score") or 0) >= 90 for r in valid) / n
    leadership_score = _clamp(0.65*_clamp(pct75/40*100) + 0.35*_clamp(pct90/20*100))

    # Broad momentum avoids being fooled by a capitalization-weighted index that
    # remains strong while the median stock deteriorates.
    pos1m = 100.0 * sum(float(r.get("return_1m_pct") or 0) > 0 for r in valid) / n
    pos3m = 100.0 * sum(float(r.get("return_3m_pct") or 0) > 0 for r in valid) / n
    momentum_score = _clamp(0.55*pos1m + 0.45*pos3m)

    # QQQ index structure, drawdown, and realized volatility.
    close = benchmark_close.dropna()
    latest = _scalar(close.iloc[-1])
    sma20 = _scalar(close.rolling(20).mean().iloc[-1])
    sma50 = _scalar(close.rolling(50).mean().iloc[-1])
    sma200 = _scalar(close.rolling(200).mean().iloc[-1])
    index_trend_score = (
        (20 if latest > sma20 else 0)
        + (25 if latest > sma50 else 0)
        + (35 if latest > sma200 else 0)
        + (20 if sma50 > sma200 else 0)
    )

    trailing_high = _scalar(close.tail(min(252, len(close))).max(), latest)
    drawdown_pct = ((latest / trailing_high) - 1.0) * 100 if trailing_high else 0.0
    # 0% drawdown=100, -10%=70, -20%=40, -35% or worse=0.
    if drawdown_pct >= -10:
        drawdown_score = 100 + drawdown_pct*3
    elif drawdown_pct >= -20:
        drawdown_score = 70 + (drawdown_pct+10)*3
    else:
        drawdown_score = 40 + (drawdown_pct+20)*(40/15)
    drawdown_score = _clamp(drawdown_score)

    daily = close.pct_change().dropna().tail(20)
    realized_vol = _scalar(daily.std()) * math.sqrt(252) * 100 if len(daily) >= 10 else 25.0
    # <=15% annualized=100; >=45%=0.
    volatility_score = _clamp((45.0-realized_vol)/30.0*100.0)

    # Sector participation keeps the score sensitive to whether leadership is
    # broad across industries rather than concentrated in one pocket.
    sector_values = [float(v) for v in (sector_scores or {}).values() if v is not None]
    sector_participation = (
        100.0 * sum(v >= 60 for v in sector_values) / len(sector_values)
        if sector_values else 50.0
    )

    components = {
        "index_trend": round(index_trend_score, 1),
        "market_breadth": round(breadth_score, 1),
        "leadership_health": round(leadership_score, 1),
        "broad_momentum": round(momentum_score, 1),
        "drawdown_resilience": round(drawdown_score, 1),
        "volatility_health": round(volatility_score, 1),
        "sector_participation": round(sector_participation, 1),
    }
    weights = {
        "index_trend": 0.20,
        "market_breadth": 0.25,
        "leadership_health": 0.15,
        "broad_momentum": 0.10,
        "drawdown_resilience": 0.10,
        "volatility_health": 0.10,
        "sector_participation": 0.10,
    }
    score = round(sum(components[k]*weights[k] for k in weights), 1)
    regime, multiplier = _classify(score)

    session_date = str(close.index[-1].date()) if len(close) else datetime.now().strftime("%Y-%m-%d")
    result = {
        "score": score,
        "regime": regime,
        "shadow_capital_multiplier": multiplier,
        "shadow_capital_pct": round(multiplier*100),
        "shadow_only": True,
        "affects_live_ladders": False,
        "market_session_date": session_date,
        "components": components,
        "observations": {
            "universe_rows": len(valid),
            "pct_above_20dma": round(p20, 1),
            "pct_above_50dma": round(p50, 1),
            "pct_above_200dma": round(p200, 1),
            "pct_50dma_above_200dma": round(golden, 1),
            "pct_technical_75_plus": round(pct75, 1),
            "pct_technical_90_plus": round(pct90, 1),
            "pct_positive_1m": round(pos1m, 1),
            "pct_positive_3m": round(pos3m, 1),
            "qqq_drawdown_pct": round(drawdown_pct, 2),
            "qqq_realized_volatility_20d_pct": round(realized_vol, 2),
        },
        "methodology": "Phase 1 shadow observer; no live decision or ladder inputs consume this score.",
    }

    history = _load_history(root)
    history = [row for row in history if row.get("market_session_date") != session_date]
    history.append(result)
    history.sort(key=lambda row: row.get("market_session_date", ""))
    _save_history(root, history[-500:])
    return result
