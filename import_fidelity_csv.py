
import argparse
import csv
import hashlib
import json
from pathlib import Path
from datetime import datetime

def parse_float(value):
    if value is None:
        return None
    s = str(value).strip().replace("$", "").replace(",", "")
    if not s or s.lower() in {"processing", "pending"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None

def parse_date(value):
    s = str(value).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%b-%d-%Y", "%b %d %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return s

def make_transaction_id(tx, duplicate_index):
    raw = "|".join(str(tx.get(k, "")) for k in ["run_date", "action", "symbol", "price", "quantity", "amount", "settlement_date"])
    return hashlib.sha256((raw + "|" + str(duplicate_index)).encode()).hexdigest()[:16]

def find_latest_account_history():
    patterns = [
        "Accounts_History*.csv",
        "History_for_Account*.csv",
    ]
    search_dirs = [Path("."), Path("data/history"), Path("imports/history")]
    files = []
    for directory in search_dirs:
        if not directory.exists():
            continue
        for pattern in patterns:
            files.extend(directory.glob(pattern))
    files = [f for f in files if f.is_file()]
    if not files:
        raise FileNotFoundError("No account-history CSV found. Expected Accounts_History*.csv or History_for_Account*.csv")
    return max(files, key=lambda f: f.stat().st_mtime)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=False, default=None, help="Optional explicit Fidelity account-history CSV. If omitted, newest Accounts_History*.csv or History_for_Account*.csv is used.")
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else find_latest_account_history()
    state_path = Path("portfolio_state.json")
    tx_path = Path("transactions.json")

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    print(f"Using account-history CSV: {csv_path}")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    existing_ids = set(state.get("import_control", {}).get("imported_transaction_ids", []))
    transactions = json.loads(tx_path.read_text(encoding="utf-8")) if tx_path.exists() else []

    new_rows = []
    with csv_path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(line for line in f if line.strip())
        counts = {}
        for idx, row in enumerate(reader):
            action_text = str(row.get("Action", "")).upper()
            if "YOU BOUGHT" not in action_text and "YOU SOLD" not in action_text:
                continue
            qty = parse_float(row.get("Quantity"))
            price = parse_float(row.get("Price ($)"))
            amount = parse_float(row.get("Amount ($)"))
            symbol = str(row.get("Symbol", "")).strip().upper()
            if not symbol or qty is None or price is None or amount is None:
                continue
            tx = {
                "run_date": parse_date(row.get("Run Date")),
                "action": "BUY" if qty > 0 else "SELL",
                "symbol": symbol,
                "description": str(row.get("Description", "")).strip(),
                "type": str(row.get("Type", "")).strip(),
                "price": price,
                "quantity": qty,
                "amount": amount,
                "cash_balance": parse_float(row.get("Cash Balance ($)")),
                "cash_balance_raw": str(row.get("Cash Balance ($)", "")).strip(),
                "settlement_date": str(row.get("Settlement Date", "")).strip(),
                "source_row": idx
            }
            raw = "|".join(str(tx.get(k, "")) for k in ["run_date", "action", "symbol", "price", "quantity", "amount", "settlement_date"])
            counts[raw] = counts.get(raw, 0) + 1
            tx["duplicate_index"] = counts[raw]
            tx["transaction_id"] = make_transaction_id(tx, tx["duplicate_index"])
            if tx["transaction_id"] not in existing_ids:
                new_rows.append(tx)
                existing_ids.add(tx["transaction_id"])

    if new_rows:
        transactions = new_rows + transactions
        tx_path.write_text(json.dumps(transactions, indent=2), encoding="utf-8")

    state.setdefault("import_control", {})
    state["import_control"]["imported_transaction_ids"] = sorted(existing_ids)
    state["import_control"]["last_csv_imported"] = csv_path.name
    state["import_control"]["last_import_trade_count"] = len(new_rows)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    print(f"Imported {len(new_rows)} new Fidelity trade rows.")

if __name__ == "__main__":
    main()
