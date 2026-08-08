"""LadderIQ targeted company-news refinement layer.

This module intentionally does NOT replace the quantitative Opportunity Score.
It runs only after the broad-market scanner has produced Base OPS values, then
checks recent company news for owned positions and non-owned names with Base OPS
>= the configured threshold. Material news can refine the score within bounded
limits while preserving a complete audit trail.

Credentials:
    FINNHUB_API_KEY must be defined as a Windows/user environment variable.
    The key is never written to LadderIQ files or logs.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

FINNHUB_BASE_URL = "https://finnhub.io/api/v1/company-news"
NEWS_LOOKBACK_DAYS = 3
NEWS_SHORTLIST_MIN_BASE_OPS = 75.0
NEWS_MIN_ARTICLE_AGE_MINUTES = 0
NEWS_CACHE_MAX_AGE_MINUTES = 30
NEWS_REQUEST_PAUSE_SECONDS = 1.05
MAX_NEGATIVE_ADJUSTMENT = -15.0
MAX_POSITIVE_ADJUSTMENT = 10.0

# The rule set is deliberately event-oriented rather than generic sentiment.
# Each matched category represents a plausible financial/institutional
# transmission mechanism. Multiple articles describing the same category do not
# compound indefinitely; only the strongest signal per category is retained.
NEGATIVE_RULES = [
    ("guidance", 9.0, [
        r"cuts? (?:its )?(?:full[- ]year |annual |quarterly )?guidance",
        r"lowers? (?:its )?(?:full[- ]year |annual |quarterly )?guidance",
        r"reduces? (?:its )?(?:full[- ]year |annual |quarterly )?outlook",
        r"guidance (?:cut|lowered|reduced|miss(?:es|ed)?)",
        r"forecast(?:s|ed)? .* below .* expectations",
    ]),
    ("major customer / demand", 9.0, [
        r"major customer .* (?:cuts?|reduces?|drops?|ends?|terminates?|cancels?)",
        r"largest customer .* (?:cuts?|reduces?|drops?|ends?|terminates?|cancels?)",
        r"customer .* (?:cuts?|reduces?|drops?|ends?|terminates?|cancels?) .* (?:spend|usage|orders?|contract)",
        r"los(?:e|es|ing|t) .* (?:major|large|key) customer",
        r"(?:demand|usage|orders?) (?:slow|slows|slowing|declines?|drops?|weakens?)",
    ]),
    ("earnings / revenue", 7.0, [
        r"miss(?:es|ed)? (?:earnings|revenue|sales|profit|estimates|expectations)",
        r"earnings miss",
        r"revenue miss",
        r"profit warning",
        r"unexpected loss",
    ]),
    ("contract / partnership", 8.0, [
        r"(?:loses?|lost|ends?|terminated?|cancels?|canceled) .* (?:contract|deal|partnership|agreement)",
        r"(?:contract|deal|partnership|agreement) .* (?:terminated|cancelled|canceled|ends?)",
        r"cuts? ties with",
        r"ends? relationship with",
    ]),
    ("regulatory / legal", 7.0, [
        r"(?:doj|ftc|sec|regulator|regulatory) .* (?:probe|investigation|lawsuit|charges?|blocks?|ban|fine)",
        r"(?:investigation|lawsuit|antitrust|fraud|subpoena|fine|penalty) .* (?:company|against)",
        r"(?:ban|restriction|sanctions?|export controls?) .* (?:sales?|shipments?|products?|chips?)",
    ]),
    ("management", 6.0, [
        r"(?:ceo|cfo|chief executive|chief financial officer) (?:resigns?|steps down|leaves?|depart(?:s|ure))",
        r"unexpected .* executive departure",
    ]),
    ("product / operations", 6.0, [
        r"(?:recall|outage|security breach|data breach|cyberattack|production halt|factory shutdown)",
        r"(?:delays?|postpones?) .* (?:launch|product|shipment|production)",
    ]),
    ("financing / liquidity", 6.0, [
        r"(?:liquidity concerns?|going concern|debt covenant|credit downgrade)",
        r"(?:dilutive|dilution) .* (?:offering|issuance)",
    ]),
]

POSITIVE_RULES = [
    ("guidance", 7.0, [
        r"raises? (?:its )?(?:full[- ]year |annual |quarterly )?guidance",
        r"lifts? (?:its )?(?:full[- ]year |annual |quarterly )?outlook",
        r"guidance (?:raised|increased)",
        r"forecast(?:s|ed)? .* above .* expectations",
    ]),
    ("major customer / demand", 7.0, [
        r"(?:wins?|lands?|adds?) .* (?:major|large|key) customer",
        r"customer .* (?:expands?|increases?|boosts?) .* (?:spend|usage|orders?|contract)",
        r"(?:demand|usage|orders?) (?:accelerates?|surges?|jumps?|strengthens?)",
    ]),
    ("earnings / revenue", 5.0, [
        r"beats? (?:earnings|revenue|sales|profit|estimates|expectations)",
        r"earnings beat",
        r"revenue beat",
        r"record (?:revenue|sales|profit|bookings)",
    ]),
    ("contract / partnership", 7.0, [
        r"(?:wins?|awarded|secures?|lands?) .* (?:contract|deal|partnership|agreement)",
        r"(?:expands?|extends?|renews?) .* (?:contract|deal|partnership|agreement)",
        r"strategic partnership",
    ]),
    ("regulatory / legal", 5.0, [
        r"(?:approval|approved|cleared) .* (?:fda|regulator|regulatory)",
        r"(?:lawsuit|investigation|probe) .* (?:dismissed|closed|dropped|settled)",
    ]),
    ("product / operations", 5.0, [
        r"(?:launches?|unveils?|introduces?) .* (?:breakthrough|new|next[- ]generation)",
        r"(?:production|capacity|shipments?) .* (?:expands?|increases?|ramps?|accelerates?)",
    ]),
]

TRUSTED_SOURCE_WEIGHTS = {
    "reuters": 1.00,
    "bloomberg": 1.00,
    "wall street journal": 1.00,
    "wsj": 1.00,
    "associated press": 0.95,
    "ap news": 0.95,
    "cnbc": 0.90,
    "financial times": 0.95,
    "barron's": 0.90,
    "marketwatch": 0.85,
    "business wire": 0.95,
    "pr newswire": 0.90,
    "globenewswire": 0.90,
    "sec": 1.00,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9%$+\- ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _source_weight(source: str) -> float:
    src = (source or "").lower()
    for key, weight in TRUSTED_SOURCE_WEIGHTS.items():
        if key in src:
            return weight
    # Unknown sources can still carry useful information, but they cannot exert
    # the same influence as primary/major financial sources.
    return 0.75


def _recency_weight(article_epoch: int | float | None) -> float:
    try:
        published = datetime.fromtimestamp(float(article_epoch), tz=timezone.utc)
    except Exception:
        return 0.65
    age = _utc_now() - published
    hours = max(0.0, age.total_seconds() / 3600.0)
    if hours <= 24:
        return 1.00
    if hours <= 48:
        return 0.85
    if hours <= 72:
        return 0.70
    return 0.50


def _match_rules(text: str, rules) -> list[tuple[str, float]]:
    matches = []
    for category, severity, patterns in rules:
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            matches.append((category, severity))
    return matches


def _article_fingerprint(article: dict) -> str:
    # Finnhub often syndicates the same event through several outlets. Headline
    # normalization removes superficial punctuation/source differences.
    headline = _normalize_text(article.get("headline") or "")
    if headline:
        return hashlib.sha1(headline.encode("utf-8")).hexdigest()[:16]
    return str(article.get("id") or article.get("url") or "")


def score_articles(symbol: str, articles: list[dict]) -> dict:
    """Return a bounded material-news adjustment and an auditable explanation."""
    deduped = []
    seen = set()
    for article in sorted(articles or [], key=lambda a: a.get("datetime") or 0, reverse=True):
        fp = _article_fingerprint(article)
        if not fp or fp in seen:
            continue
        seen.add(fp)
        deduped.append(article)

    # strongest signed evidence per economic category; repeated articles about
    # the same event/category cannot endlessly compound the adjustment.
    category_effects: dict[str, float] = {}
    evidence: dict[str, dict] = {}

    for article in deduped:
        text = _normalize_text(
            " ".join([
                str(article.get("headline") or ""),
                str(article.get("summary") or ""),
                str(article.get("related") or ""),
            ])
        )
        if not text:
            continue
        source = str(article.get("source") or "Unknown")
        weight = _source_weight(source) * _recency_weight(article.get("datetime"))
        negatives = _match_rules(text, NEGATIVE_RULES)
        positives = _match_rules(text, POSITIVE_RULES)

        # One story is one event. If a single article mentions both a customer
        # loss and a guidance cut, do not count the same event twice; retain the
        # strongest transmission mechanism from that story. Independent stories
        # in different categories can still combine, subject to the global cap.
        if negatives:
            category, severity = max(negatives, key=lambda item: item[1])
            effect = -severity * weight
            if abs(effect) > abs(category_effects.get(category, 0.0)) or category_effects.get(category, 0.0) > 0:
                category_effects[category] = effect
                evidence[category] = {"sign": "negative", "article": article, "effect": effect}
        if positives:
            category, severity = max(positives, key=lambda item: item[1])
            effect = severity * weight
            current = category_effects.get(category, 0.0)
            if abs(effect) > abs(current):
                category_effects[category] = effect
                evidence[category] = {"sign": "positive", "article": article, "effect": effect}

    raw_adjustment = sum(category_effects.values())
    adjustment = round(_clamp(raw_adjustment, MAX_NEGATIVE_ADJUSTMENT, MAX_POSITIVE_ADJUSTMENT), 1)

    ranked = sorted(evidence.items(), key=lambda item: abs(item[1]["effect"]), reverse=True)
    reasons = []
    audit_articles = []
    for category, item in ranked[:3]:
        article = item["article"]
        headline = str(article.get("headline") or "").strip()
        reasons.append(f"{category}: {headline}" if headline else category)
        audit_articles.append({
            "category": category,
            "direction": item["sign"],
            "headline": headline,
            "source": article.get("source") or "Unknown",
            "url": article.get("url") or "",
            "datetime": article.get("datetime") or 0,
            "estimated_effect": round(item["effect"], 1),
        })

    if adjustment <= -8:
        level = "High Negative"
    elif adjustment < 0:
        level = "Negative"
    elif adjustment >= 6:
        level = "High Positive"
    elif adjustment > 0:
        level = "Positive"
    else:
        level = "Neutral"

    return {
        "symbol": symbol,
        "news_adjustment": adjustment,
        "news_risk_level": level,
        "news_reason": " | ".join(reasons) if reasons else "No material recent company-news event detected.",
        "news_sources": audit_articles,
        "news_articles_reviewed": len(deduped),
    }


def _cache_path(root: Path, symbol: str) -> Path:
    return root / "market_cache" / "news" / f"{symbol.upper()}.json"


def _load_cached(root: Path, symbol: str) -> dict | None:
    path = _cache_path(root, symbol)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        checked = datetime.fromisoformat(data.get("checked_at"))
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        if _utc_now() - checked <= timedelta(minutes=NEWS_CACHE_MAX_AGE_MINUTES):
            return data
    except Exception:
        return None
    return None


def _save_cached(root: Path, symbol: str, value: dict) -> None:
    path = _cache_path(root, symbol)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    tmp.replace(path)


def fetch_company_news(symbol: str, api_key: str) -> list[dict]:
    today = _utc_now().date()
    start = today - timedelta(days=NEWS_LOOKBACK_DAYS)
    params = urllib.parse.urlencode({
        "symbol": symbol.upper(),
        "from": start.isoformat(),
        "to": today.isoformat(),
    })
    request = urllib.request.Request(
        f"{FINNHUB_BASE_URL}?{params}",
        headers={
            "User-Agent": "LadderIQ/3.60 news-refinement",
            "X-Finnhub-Token": api_key,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, list) else []


def refine_news_scores(results: list[dict], holdings: set[str] | list[str], root: Path, *, min_base_ops: float = NEWS_SHORTLIST_MIN_BASE_OPS) -> dict:
    """Refine Base OPS for owned names and high-OPS candidates.

    Failure policy is fail-open: if Finnhub is unavailable or the key is absent,
    Base OPS remains the Final OPS and the broad quantitative scanner continues.
    """
    holdings = {str(s).upper() for s in holdings}
    api_key = (os.getenv("FINNHUB_API_KEY") or "").strip()

    shortlist = [
        row for row in results
        if row.get("symbol") in holdings or float(row.get("base_ops") or row.get("leadership_score") or 0) >= float(min_base_ops)
    ]
    shortlist.sort(key=lambda row: (row.get("symbol") not in holdings, -float(row.get("base_ops") or 0), row.get("symbol") or ""))

    diagnostics = {
        "enabled": bool(api_key),
        "provider": "Finnhub Company News",
        "lookback_days": NEWS_LOOKBACK_DAYS,
        "shortlist_threshold": min_base_ops,
        "shortlisted": len(shortlist),
        "owned_shortlisted": sum(1 for row in shortlist if row.get("symbol") in holdings),
        "api_requests": 0,
        "cache_hits": 0,
        "adjusted": 0,
        "negative_adjustments": 0,
        "positive_adjustments": 0,
        "errors": [],
    }

    if not api_key:
        for row in results:
            base = float(row.get("base_ops") or row.get("leadership_score") or 0)
            row.update({
                "base_ops": round(base, 1),
                "news_adjustment": 0.0,
                "final_ops": round(base, 1),
                "news_risk_level": "Not Checked",
                "news_reason": "FINNHUB_API_KEY is not configured; Base OPS retained.",
                "news_sources": [],
                "news_checked_at": None,
            })
            row["leadership_score"] = round(base, 1)
        return diagnostics

    by_symbol = {row.get("symbol"): row for row in results}
    checked_at = _utc_now().isoformat()

    for idx, row in enumerate(shortlist, start=1):
        symbol = str(row.get("symbol") or "").upper()
        base = float(row.get("base_ops") or row.get("leadership_score") or 0)
        cached = _load_cached(root, symbol)
        try:
            if cached is not None:
                scored = cached.get("score") or {}
                diagnostics["cache_hits"] += 1
            else:
                articles = fetch_company_news(symbol, api_key)
                diagnostics["api_requests"] += 1
                scored = score_articles(symbol, articles)
                _save_cached(root, symbol, {"checked_at": checked_at, "score": scored})
                # Finnhub free tier is 60 calls/minute; stay safely below it.
                if idx < len(shortlist):
                    time.sleep(NEWS_REQUEST_PAUSE_SECONDS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            diagnostics["errors"].append({"symbol": symbol, "error": str(exc)})
            scored = {
                "news_adjustment": 0.0,
                "news_risk_level": "Unavailable",
                "news_reason": "News provider unavailable; Base OPS retained.",
                "news_sources": [],
                "news_articles_reviewed": 0,
            }

        adjustment = float(scored.get("news_adjustment") or 0)
        final = round(_clamp(base + adjustment, 0.0, 100.0), 1)
        row.update({
            "base_ops": round(base, 1),
            "news_adjustment": round(adjustment, 1),
            "final_ops": final,
            "news_risk_level": scored.get("news_risk_level") or "Neutral",
            "news_reason": scored.get("news_reason") or "No material recent company-news event detected.",
            "news_sources": scored.get("news_sources") or [],
            "news_articles_reviewed": int(scored.get("news_articles_reviewed") or 0),
            "news_checked_at": checked_at,
            "leadership_score": final,
            "qualified_candidate_raw": final >= 95,
            "qualified_100_raw": final >= 100,
            "action": "ATTACK" if final >= 90 else "ACCUMULATE" if final >= 75 else "HOLD" if final >= 60 else "REPLACE_CANDIDATE",
        })
        if adjustment:
            diagnostics["adjusted"] += 1
            diagnostics["negative_adjustments"] += int(adjustment < 0)
            diagnostics["positive_adjustments"] += int(adjustment > 0)

    # Non-shortlisted rows still receive explicit Base/Final fields so the data
    # schema is consistent and auditable across the full universe.
    for row in results:
        if row.get("symbol") in {r.get("symbol") for r in shortlist}:
            continue
        base = float(row.get("base_ops") or row.get("leadership_score") or 0)
        row.update({
            "base_ops": round(base, 1),
            "news_adjustment": 0.0,
            "final_ops": round(base, 1),
            "news_risk_level": "Not Shortlisted",
            "news_reason": f"Base OPS below {min_base_ops:.0f} and position not owned; targeted news scan skipped.",
            "news_sources": [],
            "news_checked_at": None,
            "leadership_score": round(base, 1),
        })

    return diagnostics
