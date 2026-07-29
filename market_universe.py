"""Broad U.S. common-stock universe provider for LadderIQ.

The universe is sourced from the official Nasdaq Trader symbol directories.
Only common/ordinary equity issues with Yahoo-compatible symbols are retained.
A versioned local cache prevents repeated downloads while allowing filter fixes
without preserving stale malformed symbols.
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
CACHE_FILE = "market_universe_cache.json"
CACHE_DAYS = 7
CACHE_SCHEMA_VERSION = 2

# Yahoo accepts ordinary symbols and class-share symbols such as BRK-B.
# Exchange directory symbols containing $, ^, /, spaces, or other punctuation
# represent preferred/special issues and are intentionally rejected.
YAHOO_COMMON_SYMBOL = re.compile(r"^[A-Z]{1,6}(?:-[A-Z])?$")

# Security-name phrases that identify non-common issues.  Word/phrase checks are
# deliberately conservative; ordinary shares and Class A/B common stock remain.
BLOCKED_NAME_TERMS = (
    "PREFERRED", "PREFERENCE", "DEPOSITARY SH", "DEPOSITORY SH",
    "WARRANT", "RIGHTS", " RIGHT ", " UNIT ", " UNITS",
    "BENEFICIAL INTEREST", "TRUST CERTIFICATE", "BOND", "DEBENTURE",
    "NOTE DUE", "NOTES DUE", "SENIOR NOTES", "SUBORDINATED NOTES",
    "EXCHANGE TRADED FUND", "ETF", "ETN", "CLOSED END FUND",
    "ACQUISITION CORP UNIT", "ACQUISITION RIGHT",
)


def _download_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 LadderIQ/3.60.2"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def normalize_yahoo_symbol(raw_symbol: str) -> str | None:
    """Return a Yahoo-compatible common-stock symbol or None.

    Legitimate class notation is normalized from BRK.B to BRK-B.  Exchange
    preferred notation such as BAC$L and DBRG$J is rejected, not translated.
    """
    raw = (raw_symbol or "").strip().upper()
    if not raw or raw.startswith("FILE CREATION TIME"):
        return None
    if any(ch in raw for ch in ("$", "^", "/", "\\", " ", "*", "+", "=")):
        return None
    normalized = raw.replace(".", "-")
    return normalized if YAHOO_COMMON_SYMBOL.fullmatch(normalized) else None


def _is_blocked_security_name(name: str) -> bool:
    padded = f" {name.upper().strip()} "
    return any(term in padded for term in BLOCKED_NAME_TERMS)


def _parse_pipe(text: str, symbol_field: str) -> tuple[list[str], dict[str, int]]:
    rows = csv.DictReader(io.StringIO(text), delimiter="|")
    symbols: list[str] = []
    stats = {
        "rows_seen": 0,
        "test_issues_removed": 0,
        "etfs_removed": 0,
        "non_common_removed": 0,
        "invalid_symbols_removed": 0,
        "accepted": 0,
    }
    for row in rows:
        stats["rows_seen"] += 1
        raw_symbol = (row.get(symbol_field) or "").strip().upper()
        if not raw_symbol or raw_symbol.startswith("FILE CREATION TIME"):
            continue
        if (row.get("Test Issue") or "N").strip().upper() == "Y":
            stats["test_issues_removed"] += 1
            continue
        if (row.get("ETF") or "N").strip().upper() == "Y":
            stats["etfs_removed"] += 1
            continue
        security_name = (row.get("Security Name") or "").strip()
        if _is_blocked_security_name(security_name):
            stats["non_common_removed"] += 1
            continue
        symbol = normalize_yahoo_symbol(raw_symbol)
        if not symbol:
            stats["invalid_symbols_removed"] += 1
            continue
        symbols.append(symbol)
        stats["accepted"] += 1
    return symbols, stats


def _read_cache(path: Path) -> tuple[list[str], dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) != CACHE_SCHEMA_VERSION:
            return [], {}
        created = datetime.fromisoformat(payload.get("as_of"))
        symbols = [s for s in (payload.get("symbols") or []) if normalize_yahoo_symbol(str(s))]
        if datetime.now() - created <= timedelta(days=CACHE_DAYS) and symbols:
            return sorted(set(symbols)), payload.get("filter_stats") or {}
    except Exception:
        pass
    return [], {}


def load_market_universe(root: Path, holdings: Iterable[str] = ()) -> tuple[list[str], str, dict]:
    """Return filtered common stocks plus all valid current holding symbols."""
    cache_path = root / CACHE_FILE
    cached, stats = _read_cache(cache_path)
    source = "official Nasdaq Trader cache"
    symbols: list[str] = cached

    if not symbols:
        try:
            nasdaq_symbols, nasdaq_stats = _parse_pipe(_download_text(NASDAQ_LISTED), "Symbol")
            other_symbols, other_stats = _parse_pipe(_download_text(OTHER_LISTED), "ACT Symbol")
            symbols = sorted(set(nasdaq_symbols + other_symbols))
            stats = {
                key: nasdaq_stats.get(key, 0) + other_stats.get(key, 0)
                for key in set(nasdaq_stats) | set(other_stats)
            }
            cache_path.write_text(json.dumps({
                "schema_version": CACHE_SCHEMA_VERSION,
                "as_of": datetime.now().isoformat(timespec="seconds"),
                "source": "Nasdaq Trader symbol directories",
                "filter_stats": stats,
                "symbols": symbols,
            }, indent=2), encoding="utf-8")
            source = "Nasdaq Trader symbol directories"
        except Exception:
            seed = root / "market_universe_seed.json"
            if seed.exists():
                raw_seed = list(json.loads(seed.read_text(encoding="utf-8")).get("symbols") or [])
                symbols = sorted({s for raw in raw_seed if (s := normalize_yahoo_symbol(str(raw)))})
                source = "packaged broad-market seed"
            else:
                symbols = []
                source = "holdings only (universe download unavailable)"

    valid_holdings = {
        symbol for raw in holdings
        if (symbol := normalize_yahoo_symbol(str(raw)))
    }
    symbols = sorted(set(symbols) | valid_holdings)
    return symbols, source, stats
