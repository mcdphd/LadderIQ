import pandas as pd
import json, glob, os, argparse
from datetime import datetime

POSITIONS_DIR='imports/positions'
POSITIONS_SEARCH_DIRS=['.', 'data/portfolio', POSITIONS_DIR]
STATE_FILE='portfolio_state.json'
OUTPUT_FILE='portfolio_positions.json'

def clean_number(value):
    if pd.isna(value): return 0.0
    s=str(value).strip().replace('\ufeff','')
    if s in ['', '--', '-', 'N/A', 'n/a', 'NA', 'na', 'Not Available']: return 0.0
    neg=s.startswith('(') and s.endswith(')')
    s=s.replace('$','').replace(',','').replace('%','').replace('/ Share','').replace(' / Share','').replace('(','').replace(')','').strip()
    try:
        v=float(s); return -v if neg else v
    except ValueError:
        return 0.0

def find_latest_csv():
    files=[]
    for directory in POSITIONS_SEARCH_DIRS:
        files += glob.glob(os.path.join(directory, 'Portfolio_Positions*.csv'))
    files=list(dict.fromkeys(files))
    if not files:
        raise FileNotFoundError('No Fidelity positions CSV found. Expected Portfolio_Positions*.csv in the project root, data/portfolio, or imports/positions.')
    return max(files, key=os.path.getmtime)

def infer_as_of(filename):
    import re
    base=os.path.basename(filename)
    # handles Portfolio_Positions_Jun-09-2026.csv
    m=re.search(r'([A-Za-z]{3})-(\d{1,2})-(\d{4})', base)
    if m:
        try:
            return datetime.strptime('-'.join(m.groups()), '%b-%d-%Y').strftime('%Y-%m-%d')
        except Exception:
            pass
    return datetime.now().strftime('%Y-%m-%d')

def priority_for(symbol):
    if symbol in {'TSM','PANW'}: return 'P1'
    if symbol in {'ANET','NVDA'}: return 'P2'
    if symbol == 'SPCX': return 'SS'
    return 'P3'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--csv', default=None)
    args=parser.parse_args()
    latest_file=args.csv if args.csv else find_latest_csv()
    if not os.path.exists(latest_file):
        latest_file=os.path.join(POSITIONS_DIR, latest_file)
    df=pd.read_csv(latest_file, index_col=False)
    aliases={'Last price':'Last Price','Current value':'Current Value','Cost basis total':'Cost Basis Total','Average cost basis':'Average Cost Basis','Percent of account':'Percent Of Account'}
    df=df.rename(columns={k:v for k,v in aliases.items() if k in df.columns})
    required=['Symbol','Description','Quantity','Last Price','Current Value','Cost Basis Total','Average Cost Basis','Percent Of Account']
    missing=[c for c in required if c not in df.columns]
    if missing: raise KeyError(f'Missing required columns: {missing}. Available columns: {list(df.columns)}')
    portfolio={}; positions=[]; cash=0.0; pending_activity=0.0
    for _, row in df.iterrows():
        symbol=str(row['Symbol']).strip().replace('\ufeff',''); description=str(row['Description']).strip()
        if symbol in ['', 'nan']: continue
        quantity=clean_number(row['Quantity']); last_price=clean_number(row['Last Price']); current_value=clean_number(row['Current Value']); cost_basis_total=clean_number(row['Cost Basis Total']); avg_cost=clean_number(row['Average Cost Basis']); pct_account=clean_number(row['Percent Of Account'])
        if symbol in ['FCASH','FCASH**','HELD IN FCASH'] or 'FCASH' in symbol or 'CASH' in description.upper():
            cash += current_value; continue
        if symbol=='Pending activity' or 'PENDING ACTIVITY' in symbol.upper() or 'PENDING ACTIVITY' in description.upper():
            pending_activity += current_value; continue
        if current_value == 0 and quantity == 0 and last_price == 0 and cost_basis_total == 0:
            continue
        portfolio[symbol]={'description':description,'shares':quantity,'price':last_price,'current_value':current_value,'avg_cost':avg_cost,'cost_basis_total':cost_basis_total,'percent_of_account':pct_account}
        positions.append({'symbol':symbol,'price':last_price,'quantity':quantity,'current_value':current_value,'cost_basis':cost_basis_total})
    state={}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE,'r') as f: state=json.load(f)
    existing={p.get('symbol'):p for p in state.get('positions',[])}
    updated=[]
    for p in positions:
        old=existing.get(p['symbol'],{})
        role = 'Imported Fidelity position' if float(p.get('quantity',0) or 0) > 0 else old.get('role','Buy candidate - no current Fidelity position')
        updated.append({'symbol':p['symbol'],'price':p['price'],'quantity':p['quantity'],'current_value':p['current_value'],'cost_basis':p['cost_basis'],'priority':priority_for(p['symbol']),'role':role})
    state.setdefault('baseline_value',9913.04); state.setdefault('market_mode','BULL')
    state['as_of']=infer_as_of(latest_file); state['positions']=updated; state['cash']=round(cash,2); state['pending_activity']=round(pending_activity,2); state['effective_cash']=round(cash+pending_activity,2)
    state['priority_framework']={'version':'V15 Locked Framework','P1':['TSM','PANW'],'P2':['ANET','NVDA'],'P3':['AMZN','META'],'governance':'Leadership scanner can promote tactical names, but cannot demote strategic core holdings from P1 on one reading.','effective_cash_allocation':{'TSM':0.40,'PANW':0.30,'ANET':0.25,'NVDA':0.05}}
    state['positions_last_imported_from']=latest_file; state['positions_last_imported_at']=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(OUTPUT_FILE,'w') as f: json.dump(portfolio,f,indent=4)
    with open(STATE_FILE,'w') as f: json.dump(state,f,indent=2)
    print(f'Imported {len(portfolio)} positions from:'); print(latest_file); print(f'Cash imported: ${cash:,.2f}'); print(f'Pending activity imported: ${pending_activity:,.2f}'); print(f'Effective cash: ${cash+pending_activity:,.2f}')
    print('Updated portfolio_positions.json'); print('Updated portfolio_state.json')
if __name__=='__main__': main()
