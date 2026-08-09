"""LadderIQ v3.60.17 resilient broad-market opportunity scanner.

Key protections:
- Validates/normalizes symbols before provider calls.
- Caches benchmark, price history, fundamentals, and universe results locally.
- Refreshes only stale symbols and reuses prior valid data during outages.
- Uses bounded retries/backoff and stops new requests after a rate-limit signal.
- Never overwrites a valid leadership_scores.json with an empty/partial failure.
"""
from __future__ import annotations

import contextlib
import io
import json
import logging
import math
import pickle
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict

from market_universe import load_market_universe, normalize_yahoo_symbol
from news_refinement import refine_news_scores
from market_regime import calculate_shadow_regime
from weather_sentiment import calculate_shadow_weather

MIN_PRICE = 10.0
MIN_MARKET_CAP = 2_000_000_000
MIN_DOLLAR_VOLUME = 50_000_000
MIN_HISTORY = 220
FUNDAMENTAL_REVIEW_COUNT = 60
BATCH_SIZE = 200
BATCH_PAUSE_SECONDS = 1.25
MAX_RETRIES = 3
PRICE_CACHE_MAX_AGE_HOURS = 20
FUNDAMENTAL_CACHE_MAX_AGE_DAYS = 7
VALID_DOWNLOAD_SYMBOL = re.compile(r"^[A-Z]{1,6}(?:-[A-Z])?$")

SECTOR_ETFS = {
    "Technology": "XLK", "Healthcare": "XLV", "Financial Services": "XLF",
    "Industrials": "XLI", "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
    "Energy": "XLE", "Utilities": "XLU", "Communication Services": "XLC",
    "Basic Materials": "XLB", "Real Estate": "XLRE",
}


def scalar(value, default=0.0):
    try:
        if hasattr(value, "squeeze"):
            value = value.squeeze()
        if hasattr(value, "item"):
            value = value.item()
        return float(value)
    except Exception:
        return float(default)


def pct_change(current, prior):
    prior = scalar(prior)
    return (scalar(current) / prior - 1.0) if prior else 0.0


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_stale(path: Path, *, hours: float | None = None, days: float | None = None) -> bool:
    if not path.exists():
        return True
    age = utc_now() - datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    if hours is not None:
        return age > timedelta(hours=hours)
    if days is not None:
        return age > timedelta(days=days)
    return False


def rate_limited(text: str) -> bool:
    lowered = (text or "").lower()
    return "rate limit" in lowered or "too many requests" in lowered or "yf ratelimit" in lowered


def load_holdings(root: Path) -> list[str]:
    path = root / "portfolio_positions.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [
            s.upper() for s, row in data.items()
            if scalar(row.get("shares")) >= 0.0005 and scalar(row.get("current_value")) >= 1
        ]
    except Exception:
        return []


def quiet_yf_download(tickers, **kwargs):
    """Call yfinance while capturing provider noise for diagnostics."""
    import yfinance as yf

    stdout = io.StringIO()
    stderr = io.StringIO()
    yf_logger = logging.getLogger("yfinance")
    old_level = yf_logger.level
    yf_logger.setLevel(logging.CRITICAL)
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            data = yf.download(tickers, **kwargs)
        return data, stdout.getvalue() + "\n" + stderr.getvalue(), None
    except Exception as exc:
        return None, stdout.getvalue() + "\n" + stderr.getvalue(), exc
    finally:
        yf_logger.setLevel(old_level)


def load_pickle(path: Path):
    try:
        with path.open("rb") as fh:
            return pickle.load(fh)
    except Exception:
        return None


def save_pickle(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as fh:
        pickle.dump(value, fh, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(path)


def normalize_close(data):
    if data is None or getattr(data, "empty", True):
        return None
    try:
        close = data["Close"]
        if hasattr(close, "columns"):
            close = close.iloc[:, 0]
        close = close.dropna()
        return close if len(close) >= MIN_HISTORY else None
    except Exception:
        return None


def load_benchmark(root: Path, symbol: str = "QQQ"):
    cache_path = root / "market_cache" / f"{symbol}_1y.pkl"
    cached = load_pickle(cache_path)
    if cached is not None and not is_stale(cache_path, hours=PRICE_CACHE_MAX_AGE_HOURS):
        close = normalize_close(cached)
        if close is not None:
            return close, "cache-current", False

    delay = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        data, noise, exc = quiet_yf_download(
            symbol, period="1y", interval="1d", auto_adjust=True,
            progress=False, threads=False, timeout=20,
        )
        close = normalize_close(data)
        if close is not None:
            save_pickle(cache_path, data)
            return close, "yfinance", False
        message = f"{noise} {exc or ''}"
        if attempt < MAX_RETRIES and not rate_limited(message):
            time.sleep(delay)
            delay *= 2
        else:
            break

    if cached is not None:
        close = normalize_close(cached)
        if close is not None:
            return close, "cache-stale", True
    return None, "unavailable", True


def frame_from_batch(data, symbol: str, single: bool):
    try:
        frame = data.dropna(how="all") if single else data[symbol].dropna(how="all")
        return frame if not frame.empty else None
    except Exception:
        return None


def batch_history(root: Path, symbols: list[str], period="1y"):
    """Refresh stale symbols in large batches and fall back to per-symbol cache."""
    cache_dir = root / "market_cache" / "prices"
    cache_dir.mkdir(parents=True, exist_ok=True)

    clean_symbols: list[str] = []
    rejected: list[str] = []
    for raw in symbols:
        symbol = normalize_yahoo_symbol(str(raw))
        if symbol and VALID_DOWNLOAD_SYMBOL.fullmatch(symbol):
            clean_symbols.append(symbol)
        else:
            rejected.append(str(raw))
    clean_symbols = sorted(set(clean_symbols))

    frames = {}
    stale_symbols = []
    cache_hits = 0
    for symbol in clean_symbols:
        path = cache_dir / f"{symbol}.pkl"
        cached = load_pickle(path)
        if cached is not None:
            frame = cached.dropna(how="all")
            if not frame.empty:
                frames[symbol] = frame
                cache_hits += 1
        if cached is None or is_stale(path, hours=PRICE_CACHE_MAX_AGE_HOURS):
            stale_symbols.append(symbol)

    provider_failures: list[str] = []
    refreshed = 0
    rate_limit_detected = False

    # Make the cache behavior explicit. A small refresh batch does not mean the
    # market universe collapsed; it means most symbols already have current
    # local history and only stale/missing symbols need a provider request.
    print(
        f"  Broad-market universe requested: {len(clean_symbols):,} symbols | "
        f"current cache available: {cache_hits:,} | refresh required: {len(stale_symbols):,}"
    )

    total_batches = max(1, math.ceil(len(stale_symbols) / BATCH_SIZE))
    for batch_no, start in enumerate(range(0, len(stale_symbols), BATCH_SIZE), start=1):
        if rate_limit_detected:
            break
        chunk = stale_symbols[start:start + BATCH_SIZE]
        if not chunk:
            continue
        print(f"  Market-data refresh batch {batch_no}/{total_batches}: {len(chunk)} stale/missing symbols")

        data = None
        noise = ""
        exc = None
        delay = 2.0
        for attempt in range(1, MAX_RETRIES + 1):
            data, noise, exc = quiet_yf_download(
                chunk, period=period, interval="1d", auto_adjust=True,
                progress=False, threads=True, group_by="ticker", timeout=30,
            )
            message = f"{noise} {exc or ''}"
            if data is not None and not getattr(data, "empty", True):
                break
            if rate_limited(message):
                rate_limit_detected = True
                break
            if attempt < MAX_RETRIES:
                time.sleep(delay)
                delay *= 2

        if rate_limit_detected:
            print("  Yahoo rate limit detected; stopping new requests and using cached data.")
            break

        single = len(chunk) == 1
        for symbol in chunk:
            frame = frame_from_batch(data, symbol, single) if data is not None else None
            if frame is not None:
                frames[symbol] = frame
                save_pickle(cache_dir / f"{symbol}.pkl", frame)
                refreshed += 1
            elif symbol not in frames:
                provider_failures.append(symbol)
        if batch_no < total_batches:
            time.sleep(BATCH_PAUSE_SECONDS)

    diagnostics = {
        "requested": len(clean_symbols),
        "stale_requested": len(stale_symbols),
        "downloaded_or_cached": len(frames),
        "refreshed": refreshed,
        "cache_hits": cache_hits,
        "invalid_rejected_before_download": len(rejected),
        "provider_failures": sorted(set(provider_failures)),
        "rate_limit_detected": rate_limit_detected,
    }
    return frames, diagnostics


def technical_row(symbol: str, frame, benchmark_close) -> dict | None:
    try:
        if frame is None or benchmark_close is None or len(benchmark_close) < 126:
            return None
        close = frame["Close"].dropna()
        volume = frame["Volume"].reindex(close.index).fillna(0)
        if len(close) < MIN_HISTORY:
            return None
        price = scalar(close.iloc[-1])
        avg_volume = scalar(volume.tail(20).mean())
        dollar_volume = price * avg_volume
        if price < MIN_PRICE or dollar_volume < MIN_DOLLAR_VOLUME:
            return None
        sma20 = scalar(close.rolling(20).mean().iloc[-1])
        sma50 = scalar(close.rolling(50).mean().iloc[-1])
        sma200 = scalar(close.rolling(200).mean().iloc[-1])
        returns = {
            "1m": pct_change(price, close.iloc[-21]),
            "3m": pct_change(price, close.iloc[-63]),
            "6m": pct_change(price, close.iloc[-126]),
        }
        bprice = scalar(benchmark_close.iloc[-1])
        breturns = {
            "1m": pct_change(bprice, benchmark_close.iloc[-21]),
            "3m": pct_change(bprice, benchmark_close.iloc[-63]),
            "6m": pct_change(bprice, benchmark_close.iloc[-126]),
        }
        trend = (
            (10 if price > sma20 else 0) + (15 if price > sma50 else 0)
            + (15 if price > sma200 else 0) + (10 if sma50 > sma200 else 0)
        )
        relative = (
            (10 if returns["1m"] > breturns["1m"] else 0)
            + (15 if returns["3m"] > breturns["3m"] else 0)
            + (15 if returns["6m"] > breturns["6m"] else 0)
        )
        momentum = sum(5 for value in returns.values() if value > 0)
        technical = min(100, trend + relative + momentum)
        volatility = scalar(close.pct_change().tail(63).std()) * math.sqrt(252) * 100
        downside = max(1.0, (price - sma200) / price * 100 if price > sma200 else volatility / 3)
        expected_upside = clamp(
            (returns["3m"] * 100) * 0.45 + (returns["6m"] * 100) * 0.30
            + max(0, (price / sma50 - 1) * 100) * 0.25,
            0, 60,
        )
        return {
            "symbol": symbol, "price": round(price, 2), "sma20": round(sma20, 2),
            "sma50": round(sma50, 2), "sma200": round(sma200, 2),
            "average_daily_dollar_volume": round(dollar_volume, 2),
            "technical_score": round(technical, 1), "leadership_score": round(technical, 1),
            "return_1m_pct": round(returns["1m"] * 100, 2),
            "return_3m_pct": round(returns["3m"] * 100, 2),
            "return_6m_pct": round(returns["6m"] * 100, 2),
            "relative_1m_vs_qqq_pct": round((returns["1m"] - breturns["1m"]) * 100, 2),
            "relative_3m_vs_qqq_pct": round((returns["3m"] - breturns["3m"]) * 100, 2),
            "relative_6m_vs_qqq_pct": round((returns["6m"] - breturns["6m"]) * 100, 2),
            "above_20dma": price > sma20, "above_50dma": price > sma50,
            "above_200dma": price > sma200, "sma50_above_sma200": sma50 > sma200,
            "annualized_volatility_pct": round(volatility, 2),
            "expected_upside_pct": round(expected_upside, 2),
            "expected_downside_pct": round(downside, 2),
            "reward_to_risk": round(expected_upside / downside if downside else 0, 2),
            "return_velocity": round(expected_upside / 90.0, 4),
        }
    except Exception:
        return None


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    tmp.replace(path)


def business_quality(root: Path, symbol: str, provider_state: dict) -> dict:
    """Use a 7-day cache and stop provider calls after a rate-limit response."""
    cache_path = root / "market_cache" / "fundamentals.json"
    cache = provider_state.setdefault("fundamental_cache", load_json(cache_path, {}))
    row = cache.get(symbol)
    if row and row.get("cached_at"):
        try:
            cached_at = datetime.fromisoformat(row["cached_at"])
            if utc_now() - cached_at < timedelta(days=FUNDAMENTAL_CACHE_MAX_AGE_DAYS):
                return row["data"]
        except Exception:
            pass

    if provider_state.get("rate_limited"):
        return (row or {}).get("data") or fundamental_fallback(symbol)

    import yfinance as yf
    info = {}
    try:
        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            info = yf.Ticker(symbol).get_info() or {}
        if rate_limited(stderr.getvalue()):
            provider_state["rate_limited"] = True
    except Exception as exc:
        if rate_limited(str(exc)):
            provider_state["rate_limited"] = True

    if not info:
        return (row or {}).get("data") or fundamental_fallback(symbol)

    market_cap = scalar(info.get("marketCap"))
    revenue_growth = scalar(info.get("revenueGrowth")) * 100
    earnings_growth = scalar(info.get("earningsGrowth")) * 100
    fcf = scalar(info.get("freeCashflow"))
    operating_margin = scalar(info.get("operatingMargins")) * 100
    roe = scalar(info.get("returnOnEquity")) * 100
    debt = scalar(info.get("totalDebt"))
    cash = scalar(info.get("totalCash"))
    score = 50.0
    score += clamp(revenue_growth, -20, 30) * 0.45
    score += clamp(earnings_growth, -30, 40) * 0.30
    score += 8 if fcf > 0 else -10
    score += clamp(operating_margin, -10, 30) * 0.30
    score += clamp(roe, -20, 35) * 0.15
    if debt > 0:
        score += clamp((cash / debt) - 0.5, -0.5, 1.5) * 8
    elif cash > 0:
        score += 6
    data = {
        "business_quality": round(clamp(score), 1), "market_cap": market_cap,
        "sector": info.get("sector") or "Unknown", "industry": info.get("industry") or "Unknown",
        "company": info.get("shortName") or info.get("longName") or symbol,
        "revenue_growth_pct": round(revenue_growth, 2),
        "earnings_growth_pct": round(earnings_growth, 2), "free_cash_flow": fcf,
        "operating_margin_pct": round(operating_margin, 2),
        "return_on_equity_pct": round(roe, 2),
        "fundamental_disqualification": bool(market_cap and market_cap < MIN_MARKET_CAP),
        "fundamental_source": "yfinance",
    }
    cache[symbol] = {"cached_at": utc_now().isoformat(), "data": data}
    save_json(cache_path, cache)
    time.sleep(0.15)
    return data


def fundamental_fallback(symbol: str) -> dict:
    return {
        "business_quality": 50.0, "market_cap": 0, "sector": "Unknown",
        "industry": "Unknown", "company": symbol, "fundamental_disqualification": False,
        "fundamental_source": "unavailable",
    }


def sector_scores(frames, benchmark_close) -> Dict[str, float]:
    scores = {}
    for sector, ticker in SECTOR_ETFS.items():
        row = technical_row(ticker, frames.get(ticker), benchmark_close) if frames.get(ticker) is not None else None
        scores[sector] = row["technical_score"] if row else 50.0
    return scores


def preserve_existing(root: Path, reason: str) -> int:
    existing = root / "leadership_scores.json"
    if existing.exists() and existing.stat().st_size > 100:
        print(f"WARNING: {reason}")
        print("Using the latest saved leadership scores; no valid file was overwritten.")
        return 0
    print(f"ERROR: {reason}")
    print("No prior leadership_scores.json is available. Run again after the data provider recovers.")
    return 2


def main() -> int:
    root = Path(__file__).resolve().parent
    holdings = load_holdings(root)
    universe, universe_source, universe_filter_stats = load_market_universe(root, holdings)

    benchmark_close, benchmark_source, benchmark_stale = load_benchmark(root, "QQQ")
    if benchmark_close is None or len(benchmark_close) < MIN_HISTORY:
        return preserve_existing(root, "QQQ benchmark is unavailable because Yahoo is rate-limiting requests.")

    scan_symbols = sorted(set(universe) | set(SECTOR_ETFS.values()))
    frames, download_diagnostics = batch_history(root, scan_symbols)
    if not frames:
        return preserve_existing(root, "No usable market histories were available from Yahoo or the local cache.")

    technical = []
    for symbol in universe:
        row = technical_row(symbol, frames.get(symbol), benchmark_close) if frames.get(symbol) is not None else None
        if row:
            technical.append(row)
    if not technical:
        return preserve_existing(root, "The scan produced no eligible technical rows; retaining the prior results.")

    technical.sort(
        key=lambda r: (r["technical_score"], r["reward_to_risk"], r["average_daily_dollar_volume"]),
        reverse=True,
    )
    sectors = sector_scores(frames, benchmark_close)
    reviewed = {r["symbol"] for r in technical[:FUNDAMENTAL_REVIEW_COUNT]} | set(holdings)
    provider_state = {"rate_limited": bool(download_diagnostics.get("rate_limit_detected"))}
    results = []
    errors = []

    for row in technical:
        if row["symbol"] in reviewed:
            try:
                row.update(business_quality(root, row["symbol"], provider_state))
            except Exception as exc:
                errors.append({"symbol": row["symbol"], "error": str(exc)})
                row.update(fundamental_fallback(row["symbol"]))
        else:
            row.update(fundamental_fallback(row["symbol"]))

        sector_score = sectors.get(row.get("sector"), 50.0)
        risk_score = clamp(100 - row["annualized_volatility_pct"])
        composite = (
            0.45 * row["technical_score"] + 0.30 * row["business_quality"]
            + 0.15 * sector_score + 0.10 * clamp(row["reward_to_risk"] * 25)
        )
        quality_verified = row.get("fundamental_source") in {"yfinance", "cache"}
        eligible = (
            row["price"] >= MIN_PRICE
            and row["average_daily_dollar_volume"] >= MIN_DOLLAR_VOLUME
            and (row["market_cap"] == 0 or row["market_cap"] >= MIN_MARKET_CAP)
            and row["business_quality"] >= 70
            and quality_verified
            and not row["fundamental_disqualification"]
        )
        display_ops = (
            100.0 if eligible and composite >= 82 and row["technical_score"] >= 90
            and row["reward_to_risk"] >= 1.0 else round(clamp(composite), 1)
        )
        row.update({
            "sector_leadership_score": round(sector_score, 1), "risk_score": round(risk_score, 1),
            "composite_score": round(composite, 1),
            # Base OPS remains the untouched quantitative score. The targeted
            # news-refinement layer runs after the full base scan and writes the
            # bounded Final OPS back to leadership_score for downstream logic.
            "base_ops": display_ops, "news_adjustment": 0.0, "final_ops": display_ops,
            "leadership_score": display_ops,
            "candidate_eligible": eligible, "qualified_candidate_raw": display_ops >= 95, "qualified_100_raw": display_ops >= 100,
            "action": "ATTACK" if display_ops >= 90 else "ACCUMULATE" if display_ops >= 75
            else "HOLD" if display_ops >= 60 else "REPLACE_CANDIDATE",
        })
        results.append(row)

    # Phase 1 targeted news refinement: scan only owned positions plus names
    # whose Base OPS is already high enough to influence allocation decisions.
    # If Finnhub is unavailable, this fails open and retains Base OPS.
    news_diagnostics = refine_news_scores(results, set(holdings), root, min_base_ops=75.0)

    # Phase 1 shadow market-regime observer. This is deliberately calculated
    # after the full broad-market scan but is NOT consumed by OPS, confirmation,
    # recommendations, ladder prices, ladder sizes, or capital allocation.
    shadow_regime = calculate_shadow_regime(results, benchmark_close, sectors, root)
    shadow_weather = calculate_shadow_weather(root)

    results.sort(
        key=lambda r: (r["leadership_score"], r["return_velocity"], r["reward_to_risk"], r["business_quality"]),
        reverse=True,
    )
    owned = set(holdings)
    market_mode = "NEUTRAL"
    latest = scalar(benchmark_close.iloc[-1])
    sma50 = scalar(benchmark_close.rolling(50).mean().iloc[-1])
    sma200 = scalar(benchmark_close.rolling(200).mean().iloc[-1])
    if latest > sma200 * 1.05 and sma50 > sma200:
        market_mode = "BULL"
    elif latest < sma200:
        market_mode = "BEAR"

    payload = {
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_session_date": str(benchmark_close.index[-1].date()),
        "source": "yfinance + local cache + Nasdaq Trader + Finnhub targeted company news",
        "benchmark_source": benchmark_source,
        "benchmark_stale": benchmark_stale,
        "universe_source": universe_source,
        "universe_count": len(universe),
        "universe_filter_stats": universe_filter_stats,
        "download_diagnostics": download_diagnostics,
        "news_diagnostics": news_diagnostics,
        "shadow_market_regime": shadow_regime,
        "shadow_weather_sentiment": shadow_weather,
        "eligible_technical_count": len(technical),
        "benchmark": "QQQ",
        "market_mode": market_mode,
        "sector_leadership": sectors,
        "current_leaders": [r for r in results if r["symbol"] in owned],
        "emerging_leaders": [r for r in results if r["symbol"] not in owned and r["candidate_eligible"]][:50],
        "weakening_leaders": [r for r in results if r["symbol"] in owned and r["leadership_score"] < 70],
        "scores": results,
        "errors": errors,
        "rules": {
            "candidate_discovery": "automatic broad-market discovery; watchlist membership is ignored",
            "candidate_qualification": "non-owned, eligible and OPS >=95; OPS 90-94 is shown as emerging; exact 100 remains elite",
            "confirmation": "two distinct market sessions; immediate severe-risk override",
            "news_refinement": "owned positions + Base OPS >=75; material company news adjusts OPS within -15/+10; Base and Final OPS are preserved",
            "shadow_market_regime": "Phase 1 observer only; score and hypothetical capital multiplier are logged but do not affect live ladders or OPS",
            "shadow_weather_sentiment": "Phase 1 research-only Northeast weather hypothesis; logged but never affects OPS, recommendations, ladders, or capital",
        },
    }
    save_json(root / "leadership_scores.json", payload)

    print(
        f"Generated leadership_scores.json from {len(universe):,} valid common-stock symbols; "
        f"{len(technical):,} passed price/liquidity/history screens."
    )
    removed = sum(
        int(universe_filter_stats.get(k, 0))
        for k in ("test_issues_removed", "etfs_removed", "non_common_removed", "invalid_symbols_removed")
    )
    failures = len(download_diagnostics.get("provider_failures") or [])
    print(
        f"Universe hygiene: {removed:,} non-common/invalid issues excluded; "
        f"{download_diagnostics.get('cache_hits', 0):,} cache hits; "
        f"{download_diagnostics.get('refreshed', 0):,} refreshed; {failures:,} unavailable."
    )
    print(
        f"News refinement: {news_diagnostics.get('shortlisted', 0)} shortlisted | "
        f"{news_diagnostics.get('api_requests', 0)} Finnhub requests | "
        f"{news_diagnostics.get('cache_hits', 0)} news-cache hits | "
        f"{news_diagnostics.get('adjusted', 0)} material OPS adjustments."
    )
    if not news_diagnostics.get('enabled'):
        print("NOTICE: FINNHUB_API_KEY is not available; Base OPS was retained without news refinement.")
    if news_diagnostics.get('errors'):
        print(f"News lookup warnings: {len(news_diagnostics['errors'])}; affected symbols retained Base OPS.")

    print(
        f"Shadow Market Regime: {shadow_regime.get('score', 0):.1f}/100 · "
        f"{shadow_regime.get('regime', 'Pending')} · hypothetical buy-capital "
        f"{shadow_regime.get('shadow_capital_pct', 100)}% (SHADOW ONLY; live ladders unchanged)."
    )
    ws = shadow_weather.get("score")
    ws_text = f"{ws:.1f}/100" if isinstance(ws, (int, float)) else "unavailable"
    print(
        f"Shadow Northeast Weather Sentiment: {ws_text} · {shadow_weather.get('signal', 'Unavailable')} · "
        f"target {shadow_weather.get('target_session_date')} (SHADOW ONLY; no trading impact)."
    )

    print("Top automatically discovered opportunities:")
    for row in payload["emerging_leaders"][:10]:
        news_note = f" | News {row.get('news_adjustment', 0):+0.1f}" if row.get('news_adjustment') else ""
        print(
            f"  {row['symbol']}: OPS {row['leadership_score']:.0f} "
            f"(Base {row.get('base_ops', row['leadership_score']):.0f}{news_note}) | "
            f"{row['sector']} | BQ {row['business_quality']:.0f}"
        )
    if provider_state.get("rate_limited"):
        print("NOTICE: Yahoo rate limiting was detected. Cached data was used where available.")
    if errors:
        print(f"Fundamental lookup warnings: {len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
