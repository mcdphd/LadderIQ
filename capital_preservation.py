"""LadderIQ Phase 1 capital-preservation shadow observer.

Calculates a 0-100 recession/crisis risk score and logs it for research.  Phase 1
never changes live OPS, recommendations, ladder prices, ladder sizes, or capital
allocation.  Phase 2 activation is intentionally deferred until backtesting and
live-shadow validation are complete.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

HISTORY_FILE = "capital_preservation_history.json"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def _clamp(v, lo=0.0, hi=100.0):
    try: v=float(v)
    except Exception: v=0.0
    return max(lo, min(hi, v))


def _load_history(root: Path):
    try:
        x=json.loads((root/HISTORY_FILE).read_text(encoding="utf-8"))
        return x if isinstance(x,list) else []
    except Exception:
        return []


def _save_history(root: Path, rows):
    path=root/HISTORY_FILE
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    tmp.replace(path)


def _fred(series: str):
    """Return chronological (date,value) rows. Fails open if FRED is unavailable."""
    try:
        req=Request(FRED_URL.format(series), headers={"User-Agent":"LadderIQ/1.0"})
        with urlopen(req, timeout=6) as r:
            text=r.read().decode("utf-8", errors="replace")
        out=[]
        for row in csv.DictReader(io.StringIO(text)):
            raw=row.get(series)
            if raw in (None,"","."): continue
            try: out.append((row.get("DATE") or row.get("observation_date"), float(raw)))
            except Exception: pass
        return out
    except Exception:
        return []


def _latest(rows, default=None):
    return rows[-1][1] if rows else default


def _change(rows, periods, default=0.0):
    if len(rows) <= periods: return default
    return rows[-1][1] - rows[-1-periods][1]


def _pct_change(rows, periods, default=0.0):
    if len(rows) <= periods or not rows[-1-periods][1]: return default
    return (rows[-1][1]/rows[-1-periods][1]-1.0)*100.0


def _classify(score: float):
    if score >= 80: return "Crisis", 5
    if score >= 65: return "Recession", 15
    if score >= 45: return "Preservation", 40
    if score >= 25: return "Caution", 75
    return "Growth", 100


def calculate_shadow_capital_preservation(shadow_market_regime: dict, root: Path) -> dict:
    """Four-pillar recession/crisis observer: market, economy, financial stress, leadership."""
    mr=shadow_market_regime or {}
    comp=mr.get("components") or {}
    obs=mr.get("observations") or {}

    # Pillar 1: market deterioration. Existing market-regime health is inverted.
    market_health=float(mr.get("score") if mr.get("score") is not None else 50.0)
    market_risk=_clamp(100.0-market_health)

    # Pillar 4: broad leadership/breadth deterioration, independently exposed.
    breadth=float(comp.get("market_breadth",50.0))
    leadership=float(comp.get("leadership_health",50.0))
    momentum=float(comp.get("broad_momentum",50.0))
    sector=float(comp.get("sector_participation",50.0))
    leadership_risk=_clamp(100.0-(0.35*breadth+0.30*leadership+0.20*momentum+0.15*sector))

    # Pillar 2: economy. Use public FRED series requiring no API key.
    sahm=_fred("SAHMREALTIME")
    unrate=_fred("UNRATE")
    payems=_fred("PAYEMS")
    indpro=_fred("INDPRO")
    econ_parts=[]; econ_detail={}; sources_ok=[]
    if sahm:
        v=_latest(sahm,0); econ_detail["sahm_rule_pp"]=round(v,3); sources_ok.append("SAHMREALTIME")
        econ_parts.append(_clamp(v/0.50*100.0))
    if unrate:
        ch=_change(unrate,3); econ_detail["unemployment_3m_change_pp"]=round(ch,3); sources_ok.append("UNRATE")
        econ_parts.append(_clamp((ch+0.10)/0.70*100.0))
    if payems:
        pc=_pct_change(payems,3); econ_detail["payroll_3m_pct"]=round(pc,3); sources_ok.append("PAYEMS")
        econ_parts.append(_clamp((0.60-pc)/0.80*100.0))
    if indpro:
        pc=_pct_change(indpro,6); econ_detail["industrial_production_6m_pct"]=round(pc,3); sources_ok.append("INDPRO")
        econ_parts.append(_clamp((1.5-pc)/4.0*100.0))
    economic_risk=round(sum(econ_parts)/len(econ_parts),1) if econ_parts else 50.0

    # Pillar 3: financial stress / credit. Positive stress and wider spreads = higher risk.
    stlfsi=_fred("STLFSI4")
    hy=_fred("BAMLH0A0HYM2")
    curve=_fred("T10Y3M")
    vix=_fred("VIXCLS")
    fin_parts=[]; fin_detail={}
    if stlfsi:
        v=_latest(stlfsi,0); fin_detail["stl_fsi"]=round(v,3); sources_ok.append("STLFSI4")
        fin_parts.append(_clamp((v+0.5)/3.0*100.0))
    if hy:
        v=_latest(hy,4); fin_detail["high_yield_oas_pct"]=round(v,3); sources_ok.append("BAMLH0A0HYM2")
        fin_parts.append(_clamp((v-3.0)/7.0*100.0))
    if curve:
        v=_latest(curve,0); fin_detail["10y_3m_spread_pp"]=round(v,3); sources_ok.append("T10Y3M")
        # Deep inversion is a warning; positive curve alone is not crisis stress.
        fin_parts.append(_clamp((-v)/1.5*70.0))
    if vix:
        v=_latest(vix,20); fin_detail["vix"]=round(v,2); sources_ok.append("VIXCLS")
        fin_parts.append(_clamp((v-15.0)/35.0*100.0))
    financial_risk=round(sum(fin_parts)/len(fin_parts),1) if fin_parts else 50.0

    pillars={
        "market_deterioration":round(market_risk,1),
        "economic_deterioration":round(economic_risk,1),
        "financial_stress":round(financial_risk,1),
        "leadership_stress":round(leadership_risk,1),
    }
    score=round(sum(pillars.values())/4.0,1)
    regime, capital_pct=_classify(score)

    reasons=[]
    if pillars["market_deterioration"]>=45: reasons.append("market structure is deteriorating")
    if pillars["economic_deterioration"]>=45: reasons.append("economic indicators are weakening")
    if pillars["financial_stress"]>=45: reasons.append("credit/financial stress is elevated")
    if pillars["leadership_stress"]>=45: reasons.append("breadth and leadership are weakening")
    if not reasons: reasons.append("no broad capital-preservation trigger is active")

    session_date=mr.get("market_session_date") or datetime.now().strftime("%Y-%m-%d")
    result={
        "score":score,"regime":regime,"shadow_capital_pct":capital_pct,
        "shadow_only":True,"affects_live_ladders":False,"market_session_date":session_date,
        "pillars":pillars,"economic_detail":econ_detail,"financial_detail":fin_detail,
        "data_sources_ok":sorted(set(sources_ok)),
        "data_quality":"full" if len(set(sources_ok))>=6 else ("partial" if sources_ok else "fallback"),
        "summary":"; ".join(reasons).capitalize()+".",
        "phase2_policy":"Only Phase 2 may allow preservation-driven below-cost sells; every such rung must include a specific rationale.",
        "methodology":"Phase 1 shadow only: four equally weighted pillars; no live ladder, OPS, recommendation, or allocation impact.",
    }
    history=_load_history(root)
    history=[x for x in history if x.get("market_session_date")!=session_date]
    history.append(result); history.sort(key=lambda x:x.get("market_session_date",""))
    _save_history(root, history[-500:])
    return result
