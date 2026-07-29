"""LadderIQ v3.60 broad-market opportunity scanner.

Discovers candidates from the investable U.S. market rather than a user
watchlist. It applies liquidity, technical, business-quality, sector-leadership,
risk and return-velocity rules, then emits a normalized 0-100 OPS.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable
import contextlib
import io
import logging
import re

from market_universe import load_market_universe, normalize_yahoo_symbol

MIN_PRICE = 10.0
MIN_MARKET_CAP = 2_000_000_000
MIN_DOLLAR_VOLUME = 50_000_000
MIN_HISTORY = 220
FUNDAMENTAL_REVIEW_COUNT = 125
BATCH_SIZE = 75
VALID_DOWNLOAD_SYMBOL = re.compile(r"^[A-Z]{1,6}(?:-[A-Z])?$")

SECTOR_ETFS = {
    "Technology": "XLK", "Healthcare": "XLV", "Financial Services": "XLF",
    "Industrials": "XLI", "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
    "Energy": "XLE", "Utilities": "XLU", "Communication Services": "XLC",
    "Basic Materials": "XLB", "Real Estate": "XLRE",
}


def scalar(value, default=0.0):
    try:
        if hasattr(value, "squeeze"): value = value.squeeze()
        if hasattr(value, "item"): value = value.item()
        return float(value)
    except Exception:
        return float(default)


def pct_change(current, prior):
    prior = scalar(prior)
    return (scalar(current) / prior - 1.0) if prior else 0.0


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def load_holdings(root: Path) -> list[str]:
    path = root / "portfolio_positions.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [s.upper() for s, row in data.items() if scalar(row.get("shares")) >= 0.0005 and scalar(row.get("current_value")) >= 1]
    except Exception:
        return []


def batch_history(symbols: list[str], period="1y"):
    """Download price history quietly in validated batches.

    Yahoo/yfinance can emit a full warning block for every invalid exchange
    issue.  The universe is filtered first, and expected provider noise is
    captured so the console receives one useful summary instead.
    """
    import yfinance as yf

    clean_symbols = []
    rejected = []
    for raw in symbols:
        symbol = normalize_yahoo_symbol(str(raw))
        if symbol and VALID_DOWNLOAD_SYMBOL.fullmatch(symbol):
            clean_symbols.append(symbol)
        else:
            rejected.append(str(raw))
    clean_symbols = sorted(set(clean_symbols))

    frames = {}
    provider_failures = []
    yf_logger = logging.getLogger("yfinance")
    old_level = yf_logger.level
    yf_logger.setLevel(logging.CRITICAL)
    try:
        for start in range(0, len(clean_symbols), BATCH_SIZE):
            chunk = clean_symbols[start:start + BATCH_SIZE]
            if not chunk:
                continue
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    data = yf.download(
                        chunk, period=period, interval="1d", auto_adjust=True,
                        progress=False, threads=True, group_by="ticker",
                    )
            except Exception:
                provider_failures.extend(chunk)
                continue

            if len(chunk) == 1:
                symbol = chunk[0]
                try:
                    frame = data.dropna(how="all")
                    if not frame.empty:
                        frames[symbol] = frame
                    else:
                        provider_failures.append(symbol)
                except Exception:
                    provider_failures.append(symbol)
            else:
                for symbol in chunk:
                    try:
                        frame = data[symbol].dropna(how="all")
                        if not frame.empty:
                            frames[symbol] = frame
                        else:
                            provider_failures.append(symbol)
                    except Exception:
                        provider_failures.append(symbol)
    finally:
        yf_logger.setLevel(old_level)

    diagnostics = {
        "requested": len(clean_symbols),
        "downloaded": len(frames),
        "invalid_rejected_before_download": len(rejected),
        "provider_failures": sorted(set(provider_failures)),
    }
    return frames, diagnostics


def technical_row(symbol: str, frame, benchmark_close) -> dict | None:
    try:
        close = frame["Close"].dropna()
        volume = frame["Volume"].reindex(close.index).fillna(0)
        if len(close) < MIN_HISTORY: return None
        price = scalar(close.iloc[-1])
        avg_volume = scalar(volume.tail(20).mean())
        dollar_volume = price * avg_volume
        if price < MIN_PRICE or dollar_volume < MIN_DOLLAR_VOLUME: return None
        sma20 = scalar(close.rolling(20).mean().iloc[-1]); sma50 = scalar(close.rolling(50).mean().iloc[-1]); sma200 = scalar(close.rolling(200).mean().iloc[-1])
        returns = {"1m": pct_change(price, close.iloc[-21]), "3m": pct_change(price, close.iloc[-63]), "6m": pct_change(price, close.iloc[-126])}
        bprice = scalar(benchmark_close.iloc[-1])
        breturns = {"1m": pct_change(bprice, benchmark_close.iloc[-21]), "3m": pct_change(bprice, benchmark_close.iloc[-63]), "6m": pct_change(bprice, benchmark_close.iloc[-126])}
        trend = (10 if price>sma20 else 0)+(15 if price>sma50 else 0)+(15 if price>sma200 else 0)+(10 if sma50>sma200 else 0)
        relative = (10 if returns["1m"]>breturns["1m"] else 0)+(15 if returns["3m"]>breturns["3m"] else 0)+(15 if returns["6m"]>breturns["6m"] else 0)
        momentum = sum(5 for value in returns.values() if value > 0)
        technical = min(100, trend+relative+momentum)
        volatility = scalar(close.pct_change().tail(63).std()) * math.sqrt(252) * 100
        downside = max(1.0, (price-sma200)/price*100 if price>sma200 else volatility/3)
        expected_upside = clamp((returns["3m"]*100)*0.45 + (returns["6m"]*100)*0.30 + max(0,(price/sma50-1)*100)*0.25, 0, 60)
        return {
            "symbol": symbol, "price": round(price,2), "sma20": round(sma20,2), "sma50": round(sma50,2), "sma200": round(sma200,2),
            "average_daily_dollar_volume": round(dollar_volume,2), "technical_score": round(technical,1), "leadership_score": round(technical,1),
            "return_1m_pct": round(returns["1m"]*100,2), "return_3m_pct": round(returns["3m"]*100,2), "return_6m_pct": round(returns["6m"]*100,2),
            "relative_1m_vs_qqq_pct": round((returns["1m"]-breturns["1m"])*100,2), "relative_3m_vs_qqq_pct": round((returns["3m"]-breturns["3m"])*100,2), "relative_6m_vs_qqq_pct": round((returns["6m"]-breturns["6m"])*100,2),
            "above_20dma": price>sma20, "above_50dma": price>sma50, "above_200dma": price>sma200, "sma50_above_sma200": sma50>sma200,
            "annualized_volatility_pct": round(volatility,2), "expected_upside_pct": round(expected_upside,2), "expected_downside_pct": round(downside,2),
            "reward_to_risk": round(expected_upside/downside if downside else 0,2), "return_velocity": round(expected_upside/90.0,4),
        }
    except Exception:
        return None


def business_quality(symbol: str) -> dict:
    import yfinance as yf
    info = {}
    try: info = yf.Ticker(symbol).get_info() or {}
    except Exception: pass
    market_cap = scalar(info.get("marketCap"))
    revenue_growth = scalar(info.get("revenueGrowth"))*100
    earnings_growth = scalar(info.get("earningsGrowth"))*100
    fcf = scalar(info.get("freeCashflow")); operating_margin = scalar(info.get("operatingMargins"))*100
    roe = scalar(info.get("returnOnEquity"))*100; debt = scalar(info.get("totalDebt")); cash = scalar(info.get("totalCash"))
    score = 50.0
    score += clamp(revenue_growth, -20, 30)*0.45
    score += clamp(earnings_growth, -30, 40)*0.30
    score += 8 if fcf > 0 else -10
    score += clamp(operating_margin, -10, 30)*0.30
    score += clamp(roe, -20, 35)*0.15
    if debt > 0: score += clamp((cash/debt)-0.5, -0.5, 1.5)*8
    elif cash > 0: score += 6
    score = clamp(score)
    return {"business_quality": round(score,1), "market_cap": market_cap, "sector": info.get("sector") or "Unknown", "industry": info.get("industry") or "Unknown", "company": info.get("shortName") or info.get("longName") or symbol,
            "revenue_growth_pct": round(revenue_growth,2), "earnings_growth_pct": round(earnings_growth,2), "free_cash_flow": fcf, "operating_margin_pct": round(operating_margin,2), "return_on_equity_pct": round(roe,2),
            "fundamental_disqualification": bool(market_cap and market_cap < MIN_MARKET_CAP)}


def sector_scores(frames, benchmark_close) -> Dict[str,float]:
    scores = {}
    for sector, ticker in SECTOR_ETFS.items():
        row = technical_row(ticker, frames.get(ticker), benchmark_close) if frames.get(ticker) is not None else None
        scores[sector] = row["technical_score"] if row else 50.0
    return scores


def main():
    root = Path(__file__).resolve().parent
    holdings = load_holdings(root)
    universe, universe_source, universe_filter_stats = load_market_universe(root, holdings)
    import yfinance as yf
    benchmark_data = yf.download("QQQ", period="1y", interval="1d", auto_adjust=True, progress=False, threads=False)
    benchmark_close = benchmark_data["Close"]
    if hasattr(benchmark_close,"columns"): benchmark_close=benchmark_close.iloc[:,0]
    benchmark_close=benchmark_close.dropna()
    scan_symbols = sorted(set(universe) | set(SECTOR_ETFS.values()))
    frames, download_diagnostics = batch_history(scan_symbols)
    technical = []
    for symbol in universe:
        row = technical_row(symbol, frames.get(symbol), benchmark_close) if frames.get(symbol) is not None else None
        if row: technical.append(row)
    technical.sort(key=lambda r:(r["technical_score"],r["reward_to_risk"],r["average_daily_dollar_volume"]), reverse=True)
    sectors = sector_scores(frames, benchmark_close)
    reviewed = {r["symbol"] for r in technical[:FUNDAMENTAL_REVIEW_COUNT]} | set(holdings)
    results=[]; errors=[]
    for row in technical:
        if row["symbol"] in reviewed:
            try: row.update(business_quality(row["symbol"]))
            except Exception as exc: errors.append({"symbol":row["symbol"],"error":str(exc)})
        else:
            row.update({"business_quality":50.0,"market_cap":0,"sector":"Unknown","industry":"Unknown","company":row["symbol"],"fundamental_disqualification":False})
        sector_score = sectors.get(row.get("sector"),50.0)
        risk_score = clamp(100-row["annualized_volatility_pct"])
        composite = .45*row["technical_score"] + .30*row["business_quality"] + .15*sector_score + .10*clamp(row["reward_to_risk"]*25)
        eligible = (row["price"]>=MIN_PRICE and row["average_daily_dollar_volume"]>=MIN_DOLLAR_VOLUME and (row["market_cap"]==0 or row["market_cap"]>=MIN_MARKET_CAP) and row["business_quality"]>=70 and not row["fundamental_disqualification"])
        # 100 OPS is a qualification tier, not simple arithmetic saturation.
        display_ops = 100.0 if eligible and composite>=82 and row["technical_score"]>=90 and row["reward_to_risk"]>=1.0 else round(clamp(composite),1)
        row.update({"sector_leadership_score":round(sector_score,1),"risk_score":round(risk_score,1),"composite_score":round(composite,1),"leadership_score":display_ops,"candidate_eligible":eligible,
                    "qualified_100_raw":display_ops>=100,"action":"ATTACK" if display_ops>=90 else "ACCUMULATE" if display_ops>=75 else "HOLD" if display_ops>=60 else "REPLACE_CANDIDATE"})
        results.append(row)
    results.sort(key=lambda r:(r["leadership_score"],r["return_velocity"],r["reward_to_risk"],r["business_quality"]),reverse=True)
    owned=set(holdings)
    payload={"as_of":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"market_session_date":str(benchmark_close.index[-1].date()),"source":"yfinance + Nasdaq Trader","universe_source":universe_source,"universe_count":len(universe),"universe_filter_stats":universe_filter_stats,"download_diagnostics":download_diagnostics,"eligible_technical_count":len(technical),"benchmark":"QQQ","market_mode":"BULL" if scalar(benchmark_close.iloc[-1])>scalar(benchmark_close.rolling(200).mean().iloc[-1])*1.05 and scalar(benchmark_close.rolling(50).mean().iloc[-1])>scalar(benchmark_close.rolling(200).mean().iloc[-1]) else "BEAR" if scalar(benchmark_close.iloc[-1])<scalar(benchmark_close.rolling(200).mean().iloc[-1]) else "NEUTRAL",
             "sector_leadership":sectors,"current_leaders":[r for r in results if r["symbol"] in owned],"emerging_leaders":[r for r in results if r["symbol"] not in owned and r["candidate_eligible"]][:50],"weakening_leaders":[r for r in results if r["symbol"] in owned and r["leadership_score"]<70],"scores":results,"errors":errors,
             "rules":{"candidate_discovery":"automatic broad-market discovery; watchlist membership is ignored","candidate_qualification":"non-owned, eligible, business quality >=70, technical >=90, composite >=82, reward/risk >=1","confirmation":"two distinct market sessions; immediate severe-risk override"}}
    (root/"leadership_scores.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(f"Generated leadership_scores.json from {len(universe):,} valid common-stock symbols; {len(technical):,} passed price/liquidity/history screens.")
    removed = sum(int(universe_filter_stats.get(k, 0)) for k in ("test_issues_removed", "etfs_removed", "non_common_removed", "invalid_symbols_removed"))
    failures = len(download_diagnostics.get("provider_failures") or [])
    print(f"Universe hygiene: {removed:,} non-common/invalid issues excluded before download; {failures:,} provider symbols returned no usable history.")
    print("Top automatically discovered opportunities:")
    for row in payload["emerging_leaders"][:10]: print(f"  {row['symbol']}: OPS {row['leadership_score']:.0f} | {row['sector']} | BQ {row['business_quality']:.0f}")
    if errors: print(f"Fundamental lookup warnings: {len(errors)}")

if __name__ == "__main__": main()
