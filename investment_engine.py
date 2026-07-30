"""LadderIQ v3.60.8 strategy engine.

Centralizes the broad-market opportunity confirmation, position-state logic,
ROI pacing, and recommendation-to-ladder controls.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping

ANNUAL_ROI_TARGET = 1.00
CONFIRMATION_DAYS = 2
OPPORTUNITY_THRESHOLD = 95.0
IMMEDIATE_RISK_SCORE = 45.0
STATE_FILE = "opportunity_confirmation_state.json"


def _parse_as_of(value: str | None) -> str:
    if not value:
        return date.today().isoformat()
    return str(value).split()[0]


def confirm_opportunities(
    scores: Mapping[str, Mapping], root: Path, as_of: str | None,
    threshold: float = OPPORTUNITY_THRESHOLD,
) -> Dict[str, dict]:
    """Apply a two-trading-day confirmation rule to every scanned symbol.

    Migration behavior: the first v3.60 run bootstraps the current score as
    confirmed so the dashboard does not go blank. Every later score change
    requires two consecutive dated observations. Severe deteriorations can
    trigger an immediate risk override.
    """
    path = root / STATE_FILE
    day = _parse_as_of(as_of)
    try:
        state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        state = {}
    symbols: MutableMapping[str, dict] = state.setdefault("symbols", {})
    first_migration = not bool(symbols)
    result: Dict[str, dict] = {}

    for symbol, row in scores.items():
        raw = float(row.get("leadership_score") or 0)
        prior = symbols.get(symbol, {})
        prior_raw = prior.get("observed_score")
        same_day = prior.get("last_observed") == day
        if first_migration:
            streak = CONFIRMATION_DAYS
            confirmed = raw
        elif same_day:
            streak = int(prior.get("streak") or 1)
            confirmed = float(prior.get("confirmed_score", raw))
        elif prior_raw is not None and float(prior_raw) == raw:
            streak = int(prior.get("streak") or 1) + 1
            confirmed = raw if streak >= CONFIRMATION_DAYS else float(prior.get("confirmed_score", raw))
        else:
            streak = 1
            confirmed = float(prior.get("confirmed_score", raw))

        previous_confirmed = float(prior.get("confirmed_score", confirmed))
        drop = previous_confirmed - raw
        immediate_risk = raw <= IMMEDIATE_RISK_SCORE and (drop >= 20 or not row.get("above_50dma", True))
        if immediate_risk:
            confirmed = raw
            streak = CONFIRMATION_DAYS

        qualified = confirmed >= threshold and streak >= CONFIRMATION_DAYS
        symbols[symbol] = {
            "observed_score": raw,
            "confirmed_score": confirmed,
            "streak": streak,
            "last_observed": day,
            "qualified_candidate": qualified,
            "qualified_100": confirmed >= 100 and streak >= CONFIRMATION_DAYS,
            "immediate_risk_override": immediate_risk,
        }
        result[symbol] = dict(symbols[symbol])

    state.update({
        "version": "1.0",
        "confirmation_days": CONFIRMATION_DAYS,
        "threshold": threshold,
        "elite_threshold": 100.0,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "migration_bootstrap_used": first_migration,
    })
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return result


def position_state(stock: Mapping) -> dict:
    """Classify an owned position into Harvest, Hold, Recovery, or Defensive."""
    score = float(stock.get("opportunity") or 0)
    price = float(stock.get("price") or 0)
    avg = float(stock.get("avg_cost") or 0)
    total_pl_pct = float(stock.get("total_pl_pct") or 0)
    row = stock.get("score_data") or {}
    below20 = not bool(row.get("above_20dma", score >= 75))
    below50 = not bool(row.get("above_50dma", score >= 60))
    below200 = not bool(row.get("above_200dma", score >= 45))
    override = bool(stock.get("immediate_risk_override"))

    if override or score < 45 or below200:
        name, action = "Defensive", "Reduce risk; rebuild the exit ladder from current market structure."
    elif score < 75 and (below20 or below50):
        name, action = "Recovery", "Hold the recovery ladder; do not automatically chase the price lower."
    elif score >= 90 and (total_pl_pct >= 20 or (avg > 0 and price >= avg * 1.20)):
        name, action = "Harvest", "Take profits into strength while preserving the core position."
    else:
        name, action = "Hold", "Maintain the position and wait for the next confirmed signal."
    return {"name": name, "action": action}


def roi_pace(current_return_pct: float, start_date: str, as_of: str) -> dict:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(_parse_as_of(as_of), "%Y-%m-%d").date()
    elapsed = max(1, min(365, (end - start).days))
    required_to_date = ((1 + ANNUAL_ROI_TARGET) ** (elapsed / 365.0) - 1) * 100
    current = float(current_return_pct or 0)
    remaining_days = max(1, 365 - elapsed)
    current_factor = max(0.01, 1 + current / 100)
    required_remaining = ((2.0 / current_factor) ** (365.0 / remaining_days) - 1) * 100
    pace_ratio = current / required_to_date * 100 if required_to_date > 0 else 0
    return {
        "annual_goal_pct": 100.0,
        "required_to_date_pct": required_to_date,
        "current_return_pct": current,
        "pace_ratio_pct": pace_ratio,
        "required_remaining_annualized_pct": required_remaining,
        "status": "Ahead" if current >= required_to_date else "Behind",
    }


def recommended_candidate_budget(deployable: float, candidate_count: int) -> float:
    """Aggressive but bounded capital assignment for confirmed 100-OPS names."""
    if candidate_count <= 0:
        return 0.0
    return min(float(deployable) / candidate_count, float(deployable) * 0.25)
