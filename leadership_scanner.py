import json
from datetime import datetime
from pathlib import Path

def scalar(value):
    try:
        if hasattr(value, "squeeze"):
            value = value.squeeze()
        if hasattr(value, "item"):
            return float(value.item())
        return float(value)
    except Exception:
        try:
            return float(value.values[0])
        except Exception:
            return float(value)

def safe_pct(numerator, denominator):
    try:
        denominator = float(denominator)
        if denominator == 0:
            return 0.0
        return float(numerator) / denominator
    except Exception:
        return 0.0

def download_close(ticker, period="1y"):
    import yfinance as yf
    data = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False, threads=False)
    if data is None or data.empty or "Close" not in data:
        raise RuntimeError(f"No close data returned for {ticker}")
    close = data["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    return close.dropna()

def classify_market_mode_from_state(state):
    md = state.get("market_data", {})
    try:
        q = float(md.get("qqq_price", 0))
        s50 = float(md.get("qqq_sma_50", 0))
        s200 = float(md.get("qqq_sma_200", 0))
        slope = float(md.get("qqq_sma_200_slope", 0))
        if q > s200 * 1.05 and s50 > s200:
            return "BULL"
        if q < s200 and slope < 0:
            return "BEAR"
    except Exception:
        pass
    return "NEUTRAL"

def score_one(ticker, benchmark_close):
    close = download_close(ticker)
    if len(close) < 220:
        raise RuntimeError(f"Not enough history for {ticker}; rows={len(close)}")

    price = scalar(close.iloc[-1])
    sma20 = scalar(close.rolling(20).mean().iloc[-1])
    sma50 = scalar(close.rolling(50).mean().iloc[-1])
    sma200 = scalar(close.rolling(200).mean().iloc[-1])

    ret_1m = safe_pct(price - scalar(close.iloc[-21]), scalar(close.iloc[-21])) if len(close) >= 22 else 0
    ret_3m = safe_pct(price - scalar(close.iloc[-63]), scalar(close.iloc[-63])) if len(close) >= 64 else 0
    ret_6m = safe_pct(price - scalar(close.iloc[-126]), scalar(close.iloc[-126])) if len(close) >= 127 else 0

    b_price = scalar(benchmark_close.iloc[-1])
    b_ret_1m = safe_pct(b_price - scalar(benchmark_close.iloc[-21]), scalar(benchmark_close.iloc[-21])) if len(benchmark_close) >= 22 else 0
    b_ret_3m = safe_pct(b_price - scalar(benchmark_close.iloc[-63]), scalar(benchmark_close.iloc[-63])) if len(benchmark_close) >= 64 else 0
    b_ret_6m = safe_pct(b_price - scalar(benchmark_close.iloc[-126]), scalar(benchmark_close.iloc[-126])) if len(benchmark_close) >= 127 else 0

    rel_1m = ret_1m - b_ret_1m
    rel_3m = ret_3m - b_ret_3m
    rel_6m = ret_6m - b_ret_6m

    trend_score = 0
    trend_score += 10 if price > sma20 else 0
    trend_score += 15 if price > sma50 else 0
    trend_score += 15 if price > sma200 else 0
    trend_score += 10 if sma50 > sma200 else 0

    relative_score = 0
    relative_score += 10 if rel_1m > 0 else 0
    relative_score += 15 if rel_3m > 0 else 0
    relative_score += 15 if rel_6m > 0 else 0

    momentum_score = 0
    momentum_score += 5 if ret_1m > 0 else 0
    momentum_score += 5 if ret_3m > 0 else 0
    momentum_score += 5 if ret_6m > 0 else 0

    leadership_score = min(100, trend_score + relative_score + momentum_score)

    if leadership_score >= 90:
        action = "ATTACK"
    elif leadership_score >= 75:
        action = "ACCUMULATE"
    elif leadership_score >= 60:
        action = "HOLD"
    else:
        action = "REPLACE_CANDIDATE"

    return {
        "symbol": ticker,
        "leadership_score": round(leadership_score, 1),
        "action": action,
        "price": round(price, 2),
        "sma20": round(sma20, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "return_1m_pct": round(ret_1m * 100, 2),
        "return_3m_pct": round(ret_3m * 100, 2),
        "return_6m_pct": round(ret_6m * 100, 2),
        "relative_1m_vs_qqq_pct": round(rel_1m * 100, 2),
        "relative_3m_vs_qqq_pct": round(rel_3m * 100, 2),
        "relative_6m_vs_qqq_pct": round(rel_6m * 100, 2),
        "above_20dma": price > sma20,
        "above_50dma": price > sma50,
        "above_200dma": price > sma200,
        "sma50_above_sma200": sma50 > sma200
    }

def main():
    base = Path(".")
    watchlist = json.loads((base / "watchlist.json").read_text(encoding="utf-8"))
    state = json.loads((base / "portfolio_state.json").read_text(encoding="utf-8")) if (base / "portfolio_state.json").exists() else {}

    benchmark = watchlist.get("benchmark", "QQQ")
    tickers = []
    for key in ["current_holdings", "watch_candidates"]:
        for symbol in watchlist.get(key, []):
            if symbol not in tickers:
                tickers.append(symbol)

    benchmark_close = download_close(benchmark)

    results = []
    errors = []
    for ticker in tickers:
        try:
            results.append(score_one(ticker, benchmark_close))
        except Exception as exc:
            errors.append({"symbol": ticker, "error": str(exc)})

    results = sorted(results, key=lambda x: x["leadership_score"], reverse=True)
    current_set = set(watchlist.get("current_holdings", []))
    current_scored = [r for r in results if r["symbol"] in current_set]
    watch_scored = [r for r in results if r["symbol"] not in current_set]

    payload = {
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "yfinance",
        "benchmark": benchmark,
        "market_mode": classify_market_mode_from_state(state),
        "current_leaders": current_scored[:6],
        "emerging_leaders": watch_scored[:8],
        "weakening_leaders": [r for r in current_scored if r["leadership_score"] < 70],
        "scores": results,
        "errors": errors,
        "rotation_guidance": {
            "promote_if": "watch candidate score >= 90 and current holding score < 75",
            "demote_if": "V16 guard: strategic core P1 demotes only after score <60 for 5 consecutive trading sessions AND at least two alternatives >=85; P2 demotes after score <50 for 10 consecutive sessions.",
            "bear_market_rule": "In BEAR mode, prioritize relative strength and preserve cash; do not add weak current holdings just because they are down."
        }
    }

    (base / "leadership_scores.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print("Generated leadership_scores.json")
    print("Top Current Leaders:")
    for r in payload["current_leaders"][:5]:
        print(f"  {r['symbol']}: {r['leadership_score']} / {r['action']}")
    print("Top Emerging Leaders:")
    for r in payload["emerging_leaders"][:5]:
        print(f"  {r['symbol']}: {r['leadership_score']} / {r['action']}")
    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e['symbol']}: {e['error']}")

if __name__ == "__main__":
    main()
