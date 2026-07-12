import csv, json, re, math, zipfile, shutil, os
from pathlib import Path
from datetime import datetime

VERSION='3.53.1'
BASELINE=9913.04
NEW_CONTRIBUTION=5055.52
CONTRIBUTION_DATE='2026-07-10'
PRE_CONTRIBUTION_VALUE=13017.99
TOTAL_CONTRIBUTIONS=BASELINE+NEW_CONTRIBUTION
LADDER_FOR='Monday, July 13, 2026'
DATA_AS_OF='2026-07-10 ET (After Hours)'
ROOT=Path(__file__).resolve().parent

def money_to_float(s):
    if s is None: return 0.0
    s=str(s).strip().replace('$','').replace(',','').replace('%','')
    if s in ('','nan','None'): return 0.0
    neg=False
    if s.startswith('(') and s.endswith(')'):
        neg=True; s=s[1:-1]
    if s.startswith('+'): s=s[1:]
    try: v=float(s)
    except: return 0.0
    return -v if neg else v

def fmt_money(x): return f"${float(x):,.2f}"
def fmt_pct(x): return f"{float(x):.2f}%"
def fmt_sh(x):
    x=float(x)
    return f"{x:.3f}".rstrip('0').rstrip('.')

def find_latest_positions_csv():
    files = list(ROOT.glob('Portfolio_Positions*.csv'))
    files = [f for f in files if f.is_file()]
    if not files:
        raise FileNotFoundError('No positions CSV found. Expected Portfolio_Positions*.csv')
    return max(files, key=lambda f: f.stat().st_mtime)

def read_positions():
    path=find_latest_positions_csv()
    print(f'Using positions CSV: {path}')
    pos={}; cash=0; pending=0
    with open(path, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            sym=(row.get('Symbol') or '').strip()
            if sym=='FCASH**':
                cash=money_to_float(row.get('Current Value') or row.get('Current value'))
            elif sym=='Pending activity':
                pending=money_to_float(row.get('Current Value') or row.get('Current value'))
            elif sym and sym not in ('', 'Symbol') and row.get('Quantity'):
                pos[sym]={
                    'symbol':sym,
                    'company':row.get('Description') or sym,
                    'quantity':money_to_float(row.get('Quantity')),
                    'price':money_to_float(row.get('Last Price') or row.get('Last price')),
                    'value':money_to_float(row.get('Current Value') or row.get('Current value')),
                    'today_pl':money_to_float(row.get("Today's Gain/Loss Dollar") or row.get("Today's gain/loss dollar")),
                    'today_pl_pct':money_to_float(row.get("Today's Gain/Loss Percent") or row.get("Today's gain/loss percent")),
                    'total_pl':money_to_float(row.get('Total Gain/Loss Dollar') or row.get('Total gain/loss dollar')),
                    'total_pl_pct':money_to_float(row.get('Total Gain/Loss Percent') or row.get('Total gain/loss percent')),
                    'weight':money_to_float(row.get('Percent Of Account') or row.get('Percent of account')),
                    'cost_basis':money_to_float(row.get('Cost Basis Total') or row.get('Cost basis total')),
                    'avg_cost':money_to_float(row.get('Average Cost Basis') or row.get('Average cost basis')),
                }
    return pos, cash, pending, path.name

def read_scores():
    path=ROOT/'leadership_scores.json'
    scores={}
    if path.exists():
        data=json.load(open(path))
        for bucket in ['scores','current_leaders','emerging_leaders','weakening_leaders']:
            for item in data.get(bucket,[]) or []:
                scores[item['symbol']]=item
    return scores

positions,cash,pending,pos_file=read_positions()
scores=read_scores()

def base_stock(sym, group, rank, role, status, target, subtitle=''):
    s=scores.get(sym,{})
    p=positions.get(sym,{})
    price=p.get('price') or float(s.get('price') or 0)
    qty=p.get('quantity',0.0); value=p.get('value',0.0)
    leadership=float(s.get('leadership_score', {'TSM':100,'PANW':100,'ANET':100,'NVDA':35,'AMZN':35,'ASML':100,'CRWD':90,'AMD':100,'SPCX':72,'ARM':74,'BAH':70}.get(sym,0)))
    trend='Up' if leadership>=75 else ('Lateral' if leadership>=30 else 'Down')
    if sym in ['AMZN','META']: trend='Down'
    if sym=='NVDA': trend='Lateral'
    rotation={'TSM':88,'PANW':83,'ANET':74,'NVDA':38,'AMZN':32,'ASML':98,'CRWD':92,'AMD':88,'SPCX':56,'ARM':52}.get(sym, int(max(0, leadership-20)))
    company={'TSM':'Taiwan Semiconductor Manufacturing Co.','PANW':'Palo Alto Networks','ANET':'Arista Networks','NVDA':'NVIDIA Corporation','AMZN':'Amazon.com','ASML':'ASML Holding','CRWD':'CrowdStrike Holdings','AMD':'Advanced Micro Devices','SPCX':'Space Exploration Tech','META':'Meta Platforms','ARM':'Arm Holdings','BAH':'Booz Allen Hamilton Holding Corp.'}.get(sym, p.get('company',sym))
    business_quality={'ASML':100,'TSM':99,'NVDA':98,'PANW':97,'CRWD':96,'ANET':95,'AMD':91,'AMZN':88,'SPCX':72,'ARM':83,'BAH':88}.get(sym, max(50, leadership))
    score_reason={'NVDA':'World-class AI company, but overweight and in harvest mode; new capital priority remains low.', 'AMZN':'Quality business, but currently a rotation/exit candidate.', 'TSM':'Strategic AI infrastructure leader with active accumulation priority.', 'ASML':'Strategic semiconductor monopoly-style asset and approved growth engine.', 'ANET':'AI networking leader with current leadership confirmation.', 'PANW':'Cybersecurity leader and current capital deployment candidate.', 'CRWD':'Cybersecurity growth leader and current capital deployment candidate.', 'AMD':'AI/datacenter challenger; active growth-engine candidate.', 'SPCX':'Special situation; governed by separate risk rules.', 'ARM':'Watch-list candidate; no active ladder until approved.', 'BAH':'Legacy holding from employer RSUs. No automatic buy ladder; manage with transition rules and exit discipline.'}.get(sym, 'Opportunity score controls where the next dollar goes today; business quality is tracked separately.')
    own_reason={'BAH':'Employer RSUs / Legacy Holding','SPCX':'Special Situation','ARM':'Watch List Only'}.get(sym, 'LadderIQ Selected')
    return {**p, 'symbol':sym, 'company':company, 'group':group, 'rank':rank, 'role':role, 'status':status, 'target':target, 'subtitle':subtitle, 'price':price, 'quantity':qty, 'value':value, 'leadership':leadership, 'opportunity':leadership, 'business_quality':business_quality, 'score_reason':score_reason, 'own_reason':own_reason, 'trend':trend, 'rotation':rotation, 'avg_cost':p.get('avg_cost',0), 'weight':p.get('weight',0), 'total_pl':p.get('total_pl',0), 'total_pl_pct':p.get('total_pl_pct',0), 'today_pl':p.get('today_pl',0), 'today_pl_pct':p.get('today_pl_pct',0)}

stocks=[
 base_stock('TSM','Core Compounders',1,'P1 Leader','Accumulate','40–50%','Best-in-class leader'),
 base_stock('PANW','Core Compounders',2,'P1 Leader','Accumulate','40–50%','Cybersecurity core'),
 base_stock('ANET','Tactical Compounders',1,'P2 Tactical','Accumulate','20–40%','High-growth tactical leader'),
 base_stock('NVDA','Tactical Compounders',2,'P2 Harvest','Harvest','20–40%','No fresh buy while opportunity <50'),
 base_stock('AMZN','Tactical Compounders',3,'P3 Harvest','Harvest','20–40%','Two-step exit candidate'),
 base_stock('ASML','Growth Engine',1,'Incubator','Seed','10–20%','Approved incubator'),
 base_stock('CRWD','Growth Engine',2,'Incubator','Seed','10–20%','Approved incubator'),
 base_stock('AMD','Growth Engine',3,'Incubator','Seed','10–20%','Approved incubator'),
 base_stock('SPCX','Special Situations',1,'Special','Hold','5–10%','Strategic special situation'),
 base_stock('BAH','Legacy Holdings',1,'Legacy RSU','Transition Watch','0–5%','Employer RSUs; transition plan only'),
 base_stock('ARM','Watch List',1,'Watch','Watch Only','0%','Watch only; not approved yet'),
]
# Active Holdings drive ladders; ARM remains watch-only. META removed in V43.
position_sum=sum(p['value'] for p in positions.values())
account_total=cash+pending+position_sum
effective_cash=cash+pending
deployable=effective_cash*.85
# Performance accounting: contributions are capital events, not investment gains.
# Personal ROI measures wealth growth against all contributed capital.
net_gain=account_total-TOTAL_CONTRIBUTIONS
personal_roi=(net_gain/TOTAL_CONTRIBUTIONS*100) if TOTAL_CONTRIBUTIONS else 0.0
# Time-weighted return breaks the history at the 2026-07-10 contribution.
period1_return=(PRE_CONTRIBUTION_VALUE/BASELINE)-1 if BASELINE else 0.0
period2_return=((account_total-NEW_CONTRIBUTION)/PRE_CONTRIBUTION_VALUE)-1 if PRE_CONTRIBUTION_VALUE else 0.0
twr=((1+period1_return)*(1+period2_return)-1)*100
roi=twr
capital_ledger=[
    {'date':'2026-04-07','type':'Initial contribution','amount':BASELINE,'notes':'LadderIQ inception capital'},
    {'date':CONTRIBUTION_DATE,'type':'External contribution','amount':NEW_CONTRIBUTION,'notes':'Booz Allen SPP / vested stock contribution'},
]
# Today's PL from CSV rows
today_pl=sum(v.get('today_pl',0) for v in positions.values())
today_pl_pct=today_pl/account_total*100 if account_total else 0

# QQQ benchmark + replay series for Benchmark card.
# Start date is locked at 2026-04-07; slider end date updates benchmark metrics.
QQQ_BENCHMARK={
  "symbol": "QQQ",
  "start_date": "2026-04-07",
  "end_date": "2026-07-09",
  "start_price": 588.59,
  "end_price": 723.28,
  "return_pct": 22.883501248746985,
  "portfolio_return_pct": 31.32187502521931,
  "alpha_pct": 8.438373776472325,
  "status": "Outperforming",
  "series": [
    {
      "date": "2026-04-07",
      "price": 588.59
    },
    {
      "date": "2026-04-08",
      "price": 606.09
    },
    {
      "date": "2026-04-09",
      "price": 610.19
    },
    {
      "date": "2026-04-10",
      "price": 611.07
    },
    {
      "date": "2026-04-13",
      "price": 617.39
    },
    {
      "date": "2026-04-14",
      "price": 628.6
    },
    {
      "date": "2026-04-15",
      "price": 637.4
    },
    {
      "date": "2026-04-16",
      "price": 640.47
    },
    {
      "date": "2026-04-17",
      "price": 648.85
    },
    {
      "date": "2026-04-20",
      "price": 646.79
    },
    {
      "date": "2026-04-21",
      "price": 644.33
    },
    {
      "date": "2026-04-22",
      "price": 655.11
    },
    {
      "date": "2026-04-23",
      "price": 651.42
    },
    {
      "date": "2026-04-24",
      "price": 663.88
    },
    {
      "date": "2026-04-27",
      "price": 664.23
    },
    {
      "date": "2026-04-28",
      "price": 657.55
    },
    {
      "date": "2026-04-29",
      "price": 661.57
    },
    {
      "date": "2026-04-30",
      "price": 667.74
    },
    {
      "date": "2026-05-01",
      "price": 674.15
    },
    {
      "date": "2026-05-04",
      "price": 672.88
    },
    {
      "date": "2026-05-05",
      "price": 681.61
    },
    {
      "date": "2026-05-06",
      "price": 695.77
    },
    {
      "date": "2026-05-07",
      "price": 694.94
    },
    {
      "date": "2026-05-08",
      "price": 711.23
    },
    {
      "date": "2026-05-11",
      "price": 713.29
    },
    {
      "date": "2026-05-12",
      "price": 707.24
    },
    {
      "date": "2026-05-13",
      "price": 714.71
    },
    {
      "date": "2026-05-14",
      "price": 719.79
    },
    {
      "date": "2026-05-15",
      "price": 708.93
    },
    {
      "date": "2026-05-18",
      "price": 705.88
    },
    {
      "date": "2026-05-19",
      "price": 701.53
    },
    {
      "date": "2026-05-20",
      "price": 713.15
    },
    {
      "date": "2026-05-21",
      "price": 714.51
    },
    {
      "date": "2026-05-22",
      "price": 717.54
    },
    {
      "date": "2026-05-26",
      "price": 730.28
    },
    {
      "date": "2026-05-27",
      "price": 729.45
    },
    {
      "date": "2026-05-28",
      "price": 735.6
    },
    {
      "date": "2026-05-29",
      "price": 738.31
    },
    {
      "date": "2026-06-01",
      "price": 742.74
    },
    {
      "date": "2026-06-02",
      "price": 746.16
    },
    {
      "date": "2026-06-03",
      "price": 744.21
    },
    {
      "date": "2026-06-04",
      "price": 740.61
    },
    {
      "date": "2026-06-05",
      "price": 705.06
    },
    {
      "date": "2026-06-08",
      "price": 716.07
    },
    {
      "date": "2026-06-09",
      "price": 707.83
    },
    {
      "date": "2026-06-10",
      "price": 693.69
    },
    {
      "date": "2026-06-11",
      "price": 717.12
    },
    {
      "date": "2026-06-12",
      "price": 721.34
    },
    {
      "date": "2026-06-15",
      "price": 744.0
    },
    {
      "date": "2026-06-16",
      "price": 729.86
    },
    {
      "date": "2026-06-17",
      "price": 722.51
    },
    {
      "date": "2026-06-18",
      "price": 740.62
    },
    {
      "date": "2026-06-22",
      "price": 737.95
    },
    {
      "date": "2026-06-23",
      "price": 713.65
    },
    {
      "date": "2026-06-24",
      "price": 710.62
    },
    {
      "date": "2026-06-25",
      "price": 716.38
    },
    {
      "date": "2026-06-26",
      "price": 706.52
    },
    {
      "date": "2026-06-29",
      "price": 724.08
    },
    {
      "date": "2026-06-30",
      "price": 736.4
    },
    {
      "date": "2026-07-01",
      "price": 725.17
    },
    {
      "date": "2026-07-02",
      "price": 712.6
    },
    {
      "date": "2026-07-06",
      "price": 722.82
    },
    {
      "date": "2026-07-07",
      "price": 709.43
    },
    {
      "date": "2026-07-08",
      "price": 711.44
    }
  ],
  "buy_hold_return_pct": 1.8215512861112781,
  "ladder_alpha_pct": 29.500323739108033,
  "ladder_value_added": 2924.3788923872744,
  "notes": "V54 restores full replay benchmark card after V53 regression. Slider starts 2026-04-07 and updates portfolio, QQQ, buy-and-hold, and LadderIQ value."
}
QQQ_BENCHMARK['replay_series']=[
  {
    "date": "2026-04-07",
    "portfolio_value": 9913.1,
    "portfolio_roi": 0.0,
    "qqq_price": 588.59,
    "qqq_roi": 0.0,
    "qqq_value": 9913.04,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": 0.0,
    "alpha_dollars": 0.06,
    "ladder_alpha": 0.0,
    "ladder_value_added": 0.06,
    "status": "Beating"
  },
  {
    "date": "2026-04-08",
    "portfolio_value": 10402.5,
    "portfolio_roi": 4.94,
    "qqq_price": 606.09,
    "qqq_roi": 2.97,
    "qqq_value": 10207.78,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": 1.96,
    "alpha_dollars": 194.72,
    "ladder_alpha": 4.94,
    "ladder_value_added": 489.46,
    "status": "Beating"
  },
  {
    "date": "2026-04-09",
    "portfolio_value": 10402.48,
    "portfolio_roi": 4.94,
    "qqq_price": 610.19,
    "qqq_roi": 3.67,
    "qqq_value": 10276.83,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": 1.27,
    "alpha_dollars": 125.66,
    "ladder_alpha": 4.94,
    "ladder_value_added": 489.44,
    "status": "Beating"
  },
  {
    "date": "2026-04-10",
    "portfolio_value": 10402.48,
    "portfolio_roi": 4.94,
    "qqq_price": 611.07,
    "qqq_roi": 3.82,
    "qqq_value": 10291.65,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": 1.12,
    "alpha_dollars": 110.84,
    "ladder_alpha": 4.94,
    "ladder_value_added": 489.44,
    "status": "Beating"
  },
  {
    "date": "2026-04-13",
    "portfolio_value": 10402.48,
    "portfolio_roi": 4.94,
    "qqq_price": 617.39,
    "qqq_roi": 4.89,
    "qqq_value": 10398.09,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": 0.04,
    "alpha_dollars": 4.39,
    "ladder_alpha": 4.94,
    "ladder_value_added": 489.44,
    "status": "Beating"
  },
  {
    "date": "2026-04-14",
    "portfolio_value": 10402.48,
    "portfolio_roi": 4.94,
    "qqq_price": 628.6,
    "qqq_roi": 6.8,
    "qqq_value": 10586.89,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": -1.86,
    "alpha_dollars": -184.41,
    "ladder_alpha": 4.94,
    "ladder_value_added": 489.44,
    "status": "Lagging"
  },
  {
    "date": "2026-04-15",
    "portfolio_value": 10363.78,
    "portfolio_roi": 4.55,
    "qqq_price": 637.4,
    "qqq_roi": 8.29,
    "qqq_value": 10735.1,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": -3.75,
    "alpha_dollars": -371.32,
    "ladder_alpha": 4.55,
    "ladder_value_added": 450.74,
    "status": "Lagging"
  },
  {
    "date": "2026-04-16",
    "portfolio_value": 10363.78,
    "portfolio_roi": 4.55,
    "qqq_price": 640.47,
    "qqq_roi": 8.81,
    "qqq_value": 10786.8,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": -4.27,
    "alpha_dollars": -423.03,
    "ladder_alpha": 4.55,
    "ladder_value_added": 450.74,
    "status": "Lagging"
  },
  {
    "date": "2026-04-17",
    "portfolio_value": 10363.78,
    "portfolio_roi": 4.55,
    "qqq_price": 648.85,
    "qqq_roi": 10.24,
    "qqq_value": 10927.94,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": -5.69,
    "alpha_dollars": -564.16,
    "ladder_alpha": 4.55,
    "ladder_value_added": 450.74,
    "status": "Lagging"
  },
  {
    "date": "2026-04-20",
    "portfolio_value": 10363.78,
    "portfolio_roi": 4.55,
    "qqq_price": 646.79,
    "qqq_roi": 9.89,
    "qqq_value": 10893.25,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": -5.34,
    "alpha_dollars": -529.47,
    "ladder_alpha": 4.55,
    "ladder_value_added": 450.74,
    "status": "Lagging"
  },
  {
    "date": "2026-04-21",
    "portfolio_value": 10369.79,
    "portfolio_roi": 4.61,
    "qqq_price": 644.33,
    "qqq_roi": 9.47,
    "qqq_value": 10851.81,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": -4.86,
    "alpha_dollars": -482.02,
    "ladder_alpha": 4.61,
    "ladder_value_added": 456.75,
    "status": "Lagging"
  },
  {
    "date": "2026-04-22",
    "portfolio_value": 10369.79,
    "portfolio_roi": 4.61,
    "qqq_price": 655.11,
    "qqq_roi": 11.3,
    "qqq_value": 11033.37,
    "buy_hold_value": 9913.04,
    "buy_hold_roi": 0.0,
    "alpha": -6.69,
    "alpha_dollars": -663.58,
    "ladder_alpha": 4.61,
    "ladder_value_added": 456.75,
    "status": "Lagging"
  },
  {
    "date": "2026-04-23",
    "portfolio_value": 10874.85,
    "portfolio_roi": 9.7,
    "qqq_price": 651.42,
    "qqq_roi": 10.67,
    "qqq_value": 10971.22,
    "buy_hold_value": 10181.62,
    "buy_hold_roi": 2.71,
    "alpha": -0.97,
    "alpha_dollars": -96.37,
    "ladder_alpha": 6.99,
    "ladder_value_added": 693.23,
    "status": "Lagging"
  },
  {
    "date": "2026-04-24",
    "portfolio_value": 10851.07,
    "portfolio_roi": 9.46,
    "qqq_price": 663.88,
    "qqq_roi": 12.79,
    "qqq_value": 11181.08,
    "buy_hold_value": 10181.62,
    "buy_hold_roi": 2.71,
    "alpha": -3.33,
    "alpha_dollars": -330.0,
    "ladder_alpha": 6.75,
    "ladder_value_added": 669.46,
    "status": "Lagging"
  },
  {
    "date": "2026-04-27",
    "portfolio_value": 11120.62,
    "portfolio_roi": 12.18,
    "qqq_price": 664.23,
    "qqq_roi": 12.85,
    "qqq_value": 11186.97,
    "buy_hold_value": 10263.88,
    "buy_hold_roi": 3.54,
    "alpha": -0.67,
    "alpha_dollars": -66.35,
    "ladder_alpha": 8.64,
    "ladder_value_added": 856.74,
    "status": "Lagging"
  },
  {
    "date": "2026-04-28",
    "portfolio_value": 11012.34,
    "portfolio_roi": 11.09,
    "qqq_price": 657.55,
    "qqq_roi": 11.72,
    "qqq_value": 11074.47,
    "buy_hold_value": 10263.88,
    "buy_hold_roi": 3.54,
    "alpha": -0.63,
    "alpha_dollars": -62.12,
    "ladder_alpha": 7.55,
    "ladder_value_added": 748.46,
    "status": "Lagging"
  },
  {
    "date": "2026-04-29",
    "portfolio_value": 11018.5,
    "portfolio_roi": 11.15,
    "qqq_price": 661.57,
    "qqq_roi": 12.4,
    "qqq_value": 11142.17,
    "buy_hold_value": 10279.3,
    "buy_hold_roi": 3.69,
    "alpha": -1.25,
    "alpha_dollars": -123.67,
    "ladder_alpha": 7.46,
    "ladder_value_added": 739.2,
    "status": "Lagging"
  },
  {
    "date": "2026-04-30",
    "portfolio_value": 11139.5,
    "portfolio_roi": 12.37,
    "qqq_price": 667.74,
    "qqq_roi": 13.45,
    "qqq_value": 11246.09,
    "buy_hold_value": 10287.55,
    "buy_hold_roi": 3.78,
    "alpha": -1.08,
    "alpha_dollars": -106.58,
    "ladder_alpha": 8.59,
    "ladder_value_added": 851.95,
    "status": "Lagging"
  },
  {
    "date": "2026-05-01",
    "portfolio_value": 11123.65,
    "portfolio_roi": 12.21,
    "qqq_price": 674.15,
    "qqq_roi": 14.54,
    "qqq_value": 11354.04,
    "buy_hold_value": 10215.46,
    "buy_hold_roi": 3.05,
    "alpha": -2.32,
    "alpha_dollars": -230.39,
    "ladder_alpha": 9.16,
    "ladder_value_added": 908.19,
    "status": "Lagging"
  },
  {
    "date": "2026-05-04",
    "portfolio_value": 11154.04,
    "portfolio_roi": 12.52,
    "qqq_price": 672.88,
    "qqq_roi": 14.32,
    "qqq_value": 11332.65,
    "buy_hold_value": 10205.01,
    "buy_hold_roi": 2.95,
    "alpha": -1.8,
    "alpha_dollars": -178.61,
    "ladder_alpha": 9.57,
    "ladder_value_added": 949.03,
    "status": "Lagging"
  },
  {
    "date": "2026-05-05",
    "portfolio_value": 11299.13,
    "portfolio_roi": 13.98,
    "qqq_price": 681.61,
    "qqq_roi": 15.8,
    "qqq_value": 11479.68,
    "buy_hold_value": 10205.01,
    "buy_hold_roi": 2.95,
    "alpha": -1.82,
    "alpha_dollars": -180.55,
    "ladder_alpha": 11.04,
    "ladder_value_added": 1094.12,
    "status": "Lagging"
  },
  {
    "date": "2026-05-06",
    "portfolio_value": 11475.65,
    "portfolio_roi": 15.76,
    "qqq_price": 695.77,
    "qqq_roi": 18.21,
    "qqq_value": 11718.17,
    "buy_hold_value": 10331.45,
    "buy_hold_roi": 4.22,
    "alpha": -2.45,
    "alpha_dollars": -242.52,
    "ladder_alpha": 11.54,
    "ladder_value_added": 1144.2,
    "status": "Lagging"
  },
  {
    "date": "2026-05-07",
    "portfolio_value": 11433.75,
    "portfolio_roi": 15.34,
    "qqq_price": 694.94,
    "qqq_roi": 18.07,
    "qqq_value": 11704.19,
    "buy_hold_value": 10122.93,
    "buy_hold_roi": 2.12,
    "alpha": -2.73,
    "alpha_dollars": -270.44,
    "ladder_alpha": 13.22,
    "ladder_value_added": 1310.82,
    "status": "Lagging"
  },
  {
    "date": "2026-05-08",
    "portfolio_value": 11629.74,
    "portfolio_roi": 17.32,
    "qqq_price": 711.23,
    "qqq_roi": 20.84,
    "qqq_value": 11978.54,
    "buy_hold_value": 10207.23,
    "buy_hold_roi": 2.97,
    "alpha": -3.52,
    "alpha_dollars": -348.81,
    "ladder_alpha": 14.35,
    "ladder_value_added": 1422.51,
    "status": "Lagging"
  },
  {
    "date": "2026-05-11",
    "portfolio_value": 11652.55,
    "portfolio_roi": 17.55,
    "qqq_price": 713.29,
    "qqq_roi": 21.19,
    "qqq_value": 12013.24,
    "buy_hold_value": 10213.44,
    "buy_hold_roi": 3.03,
    "alpha": -3.64,
    "alpha_dollars": -360.69,
    "ladder_alpha": 14.52,
    "ladder_value_added": 1439.1,
    "status": "Lagging"
  },
  {
    "date": "2026-05-12",
    "portfolio_value": 11578.15,
    "portfolio_roi": 16.8,
    "qqq_price": 707.24,
    "qqq_roi": 20.16,
    "qqq_value": 11911.34,
    "buy_hold_value": 10143.95,
    "buy_hold_roi": 2.33,
    "alpha": -3.36,
    "alpha_dollars": -333.2,
    "ladder_alpha": 14.47,
    "ladder_value_added": 1434.2,
    "status": "Lagging"
  },
  {
    "date": "2026-05-13",
    "portfolio_value": 11664.25,
    "portfolio_roi": 17.67,
    "qqq_price": 714.71,
    "qqq_roi": 21.43,
    "qqq_value": 12037.15,
    "buy_hold_value": 10143.95,
    "buy_hold_roi": 2.33,
    "alpha": -3.76,
    "alpha_dollars": -372.91,
    "ladder_alpha": 15.34,
    "ladder_value_added": 1520.3,
    "status": "Lagging"
  },
  {
    "date": "2026-05-14",
    "portfolio_value": 11844.63,
    "portfolio_roi": 19.49,
    "qqq_price": 719.79,
    "qqq_roi": 22.29,
    "qqq_value": 12122.71,
    "buy_hold_value": 10270.5,
    "buy_hold_roi": 3.61,
    "alpha": -2.81,
    "alpha_dollars": -278.08,
    "ladder_alpha": 15.88,
    "ladder_value_added": 1574.13,
    "status": "Lagging"
  },
  {
    "date": "2026-05-15",
    "portfolio_value": 11807.91,
    "portfolio_roi": 19.11,
    "qqq_price": 708.93,
    "qqq_roi": 20.45,
    "qqq_value": 11939.81,
    "buy_hold_value": 10196.63,
    "buy_hold_roi": 2.86,
    "alpha": -1.33,
    "alpha_dollars": -131.9,
    "ladder_alpha": 16.25,
    "ladder_value_added": 1611.28,
    "status": "Lagging"
  },
  {
    "date": "2026-05-18",
    "portfolio_value": 11784.71,
    "portfolio_roi": 18.88,
    "qqq_price": 705.88,
    "qqq_roi": 19.93,
    "qqq_value": 11888.44,
    "buy_hold_value": 10165.02,
    "buy_hold_roi": 2.54,
    "alpha": -1.05,
    "alpha_dollars": -103.73,
    "ladder_alpha": 16.34,
    "ladder_value_added": 1619.69,
    "status": "Lagging"
  },
  {
    "date": "2026-05-19",
    "portfolio_value": 11679.97,
    "portfolio_roi": 17.82,
    "qqq_price": 701.53,
    "qqq_roi": 19.19,
    "qqq_value": 11815.18,
    "buy_hold_value": 10031.92,
    "buy_hold_roi": 1.2,
    "alpha": -1.36,
    "alpha_dollars": -135.21,
    "ladder_alpha": 16.63,
    "ladder_value_added": 1648.05,
    "status": "Lagging"
  },
  {
    "date": "2026-05-20",
    "portfolio_value": 11731.9,
    "portfolio_roi": 18.35,
    "qqq_price": 713.15,
    "qqq_roi": 21.16,
    "qqq_value": 12010.88,
    "buy_hold_value": 10031.92,
    "buy_hold_roi": 1.2,
    "alpha": -2.81,
    "alpha_dollars": -278.99,
    "ladder_alpha": 17.15,
    "ladder_value_added": 1699.97,
    "status": "Lagging"
  },
  {
    "date": "2026-05-21",
    "portfolio_value": 11887.59,
    "portfolio_roi": 19.92,
    "qqq_price": 714.51,
    "qqq_roi": 21.39,
    "qqq_value": 12033.79,
    "buy_hold_value": 10122.38,
    "buy_hold_roi": 2.11,
    "alpha": -1.47,
    "alpha_dollars": -146.2,
    "ladder_alpha": 17.81,
    "ladder_value_added": 1765.21,
    "status": "Lagging"
  },
  {
    "date": "2026-05-22",
    "portfolio_value": 11936.65,
    "portfolio_roi": 20.41,
    "qqq_price": 717.54,
    "qqq_roi": 21.91,
    "qqq_value": 12084.82,
    "buy_hold_value": 10154.08,
    "buy_hold_roi": 2.43,
    "alpha": -1.49,
    "alpha_dollars": -148.17,
    "ladder_alpha": 17.98,
    "ladder_value_added": 1782.57,
    "status": "Lagging"
  },
  {
    "date": "2026-05-26",
    "portfolio_value": 11916.74,
    "portfolio_roi": 20.21,
    "qqq_price": 730.28,
    "qqq_roi": 24.07,
    "qqq_value": 12299.38,
    "buy_hold_value": 10125.15,
    "buy_hold_roi": 2.14,
    "alpha": -3.86,
    "alpha_dollars": -382.65,
    "ladder_alpha": 18.07,
    "ladder_value_added": 1791.59,
    "status": "Lagging"
  },
  {
    "date": "2026-05-27",
    "portfolio_value": 11931.47,
    "portfolio_roi": 20.36,
    "qqq_price": 729.45,
    "qqq_roi": 23.93,
    "qqq_value": 12285.41,
    "buy_hold_value": 10075.83,
    "buy_hold_roi": 1.64,
    "alpha": -3.57,
    "alpha_dollars": -353.93,
    "ladder_alpha": 18.72,
    "ladder_value_added": 1855.64,
    "status": "Lagging"
  },
  {
    "date": "2026-05-28",
    "portfolio_value": 11935.19,
    "portfolio_roi": 20.4,
    "qqq_price": 735.6,
    "qqq_roi": 24.98,
    "qqq_value": 12388.98,
    "buy_hold_value": 10048.33,
    "buy_hold_roi": 1.36,
    "alpha": -4.58,
    "alpha_dollars": -453.79,
    "ladder_alpha": 19.03,
    "ladder_value_added": 1886.86,
    "status": "Lagging"
  },
  {
    "date": "2026-05-29",
    "portfolio_value": 12061.58,
    "portfolio_roi": 21.67,
    "qqq_price": 738.31,
    "qqq_roi": 25.44,
    "qqq_value": 12434.63,
    "buy_hold_value": 10128.04,
    "buy_hold_roi": 2.17,
    "alpha": -3.76,
    "alpha_dollars": -373.04,
    "ladder_alpha": 19.51,
    "ladder_value_added": 1933.54,
    "status": "Lagging"
  },
  {
    "date": "2026-06-01",
    "portfolio_value": 12464.16,
    "portfolio_roi": 25.74,
    "qqq_price": 742.74,
    "qqq_roi": 26.19,
    "qqq_value": 12509.24,
    "buy_hold_value": 10311.16,
    "buy_hold_roi": 4.02,
    "alpha": -0.45,
    "alpha_dollars": -45.07,
    "ladder_alpha": 21.72,
    "ladder_value_added": 2153.01,
    "status": "Lagging"
  },
  {
    "date": "2026-06-02",
    "portfolio_value": 12546.74,
    "portfolio_roi": 26.57,
    "qqq_price": 746.16,
    "qqq_roi": 26.77,
    "qqq_value": 12566.84,
    "buy_hold_value": 10428.52,
    "buy_hold_roi": 5.2,
    "alpha": -0.2,
    "alpha_dollars": -20.1,
    "ladder_alpha": 21.37,
    "ladder_value_added": 2118.22,
    "status": "Lagging"
  },
  {
    "date": "2026-06-03",
    "portfolio_value": 12482.17,
    "portfolio_roi": 25.92,
    "qqq_price": 744.21,
    "qqq_roi": 26.44,
    "qqq_value": 12533.99,
    "buy_hold_value": 10301.07,
    "buy_hold_roi": 3.91,
    "alpha": -0.52,
    "alpha_dollars": -51.82,
    "ladder_alpha": 22.0,
    "ladder_value_added": 2181.11,
    "status": "Lagging"
  },
  {
    "date": "2026-06-04",
    "portfolio_value": 12158.12,
    "portfolio_roi": 22.65,
    "qqq_price": 740.61,
    "qqq_roi": 25.83,
    "qqq_value": 12473.36,
    "buy_hold_value": 10198.75,
    "buy_hold_roi": 2.88,
    "alpha": -3.18,
    "alpha_dollars": -315.24,
    "ladder_alpha": 19.77,
    "ladder_value_added": 1959.37,
    "status": "Lagging"
  },
  {
    "date": "2026-06-05",
    "portfolio_value": 12237.03,
    "portfolio_roi": 23.44,
    "qqq_price": 705.06,
    "qqq_roi": 19.79,
    "qqq_value": 11874.63,
    "buy_hold_value": 10219.83,
    "buy_hold_roi": 3.09,
    "alpha": 3.66,
    "alpha_dollars": 362.4,
    "ladder_alpha": 20.35,
    "ladder_value_added": 2017.2,
    "status": "Beating"
  },
  {
    "date": "2026-06-08",
    "portfolio_value": 12204.33,
    "portfolio_roi": 23.11,
    "qqq_price": 716.07,
    "qqq_roi": 21.66,
    "qqq_value": 12060.06,
    "buy_hold_value": 10219.83,
    "buy_hold_roi": 3.09,
    "alpha": 1.46,
    "alpha_dollars": 144.27,
    "ladder_alpha": 20.02,
    "ladder_value_added": 1984.5,
    "status": "Beating"
  },
  {
    "date": "2026-06-09",
    "portfolio_value": 11896.84,
    "portfolio_roi": 20.01,
    "qqq_price": 707.83,
    "qqq_roi": 20.26,
    "qqq_value": 11921.28,
    "buy_hold_value": 9956.78,
    "buy_hold_roi": 0.44,
    "alpha": -0.25,
    "alpha_dollars": -24.45,
    "ladder_alpha": 19.57,
    "ladder_value_added": 1940.05,
    "status": "Lagging"
  },
  {
    "date": "2026-06-10",
    "portfolio_value": 11705.36,
    "portfolio_roi": 18.08,
    "qqq_price": 693.69,
    "qqq_roi": 17.86,
    "qqq_value": 11683.14,
    "buy_hold_value": 9956.78,
    "buy_hold_roi": 0.44,
    "alpha": 0.22,
    "alpha_dollars": 22.22,
    "ladder_alpha": 17.64,
    "ladder_value_added": 1748.57,
    "status": "Beating"
  },
  {
    "date": "2026-06-11",
    "portfolio_value": 11705.36,
    "portfolio_roi": 18.08,
    "qqq_price": 717.12,
    "qqq_roi": 21.84,
    "qqq_value": 12077.74,
    "buy_hold_value": 9956.78,
    "buy_hold_roi": 0.44,
    "alpha": -3.76,
    "alpha_dollars": -372.39,
    "ladder_alpha": 17.64,
    "ladder_value_added": 1748.57,
    "status": "Lagging"
  },
  {
    "date": "2026-06-12",
    "portfolio_value": 11799.69,
    "portfolio_roi": 19.03,
    "qqq_price": 721.34,
    "qqq_roi": 22.55,
    "qqq_value": 12148.82,
    "buy_hold_value": 10060.97,
    "buy_hold_roi": 1.49,
    "alpha": -3.52,
    "alpha_dollars": -349.12,
    "ladder_alpha": 17.54,
    "ladder_value_added": 1738.72,
    "status": "Lagging"
  },
  {
    "date": "2026-06-15",
    "portfolio_value": 12039.39,
    "portfolio_roi": 21.45,
    "qqq_price": 744.0,
    "qqq_roi": 26.4,
    "qqq_value": 12530.46,
    "buy_hold_value": 10067.64,
    "buy_hold_roi": 1.56,
    "alpha": -4.95,
    "alpha_dollars": -491.07,
    "ladder_alpha": 19.89,
    "ladder_value_added": 1971.75,
    "status": "Lagging"
  },
  {
    "date": "2026-06-16",
    "portfolio_value": 12136.81,
    "portfolio_roi": 22.43,
    "qqq_price": 729.86,
    "qqq_roi": 24.0,
    "qqq_value": 12292.31,
    "buy_hold_value": 10109.79,
    "buy_hold_roi": 1.98,
    "alpha": -1.57,
    "alpha_dollars": -155.5,
    "ladder_alpha": 20.45,
    "ladder_value_added": 2027.02,
    "status": "Lagging"
  },
  {
    "date": "2026-06-17",
    "portfolio_value": 12136.91,
    "portfolio_roi": 22.43,
    "qqq_price": 722.51,
    "qqq_roi": 22.75,
    "qqq_value": 12168.52,
    "buy_hold_value": 10144.8,
    "buy_hold_roi": 2.34,
    "alpha": -0.32,
    "alpha_dollars": -31.62,
    "ladder_alpha": 20.1,
    "ladder_value_added": 1992.11,
    "status": "Lagging"
  },
  {
    "date": "2026-06-18",
    "portfolio_value": 12254.91,
    "portfolio_roi": 23.62,
    "qqq_price": 740.62,
    "qqq_roi": 25.83,
    "qqq_value": 12473.53,
    "buy_hold_value": 10148.27,
    "buy_hold_roi": 2.37,
    "alpha": -2.21,
    "alpha_dollars": -218.63,
    "ladder_alpha": 21.25,
    "ladder_value_added": 2106.64,
    "status": "Lagging"
  },
  {
    "date": "2026-06-22",
    "portfolio_value": 12346.84,
    "portfolio_roi": 24.55,
    "qqq_price": 737.95,
    "qqq_roi": 25.38,
    "qqq_value": 12428.56,
    "buy_hold_value": 10148.27,
    "buy_hold_roi": 2.37,
    "alpha": -0.82,
    "alpha_dollars": -81.73,
    "ladder_alpha": 22.18,
    "ladder_value_added": 2198.57,
    "status": "Lagging"
  },
  {
    "date": "2026-06-23",
    "portfolio_value": 11977.71,
    "portfolio_roi": 20.83,
    "qqq_price": 713.65,
    "qqq_roi": 21.25,
    "qqq_value": 12019.3,
    "buy_hold_value": 10034.13,
    "buy_hold_roi": 1.22,
    "alpha": -0.42,
    "alpha_dollars": -41.6,
    "ladder_alpha": 19.61,
    "ladder_value_added": 1943.57,
    "status": "Lagging"
  },
  {
    "date": "2026-06-24",
    "portfolio_value": 12001.66,
    "portfolio_roi": 21.07,
    "qqq_price": 710.62,
    "qqq_roi": 20.73,
    "qqq_value": 11968.27,
    "buy_hold_value": 10039.9,
    "buy_hold_roi": 1.28,
    "alpha": 0.34,
    "alpha_dollars": 33.39,
    "ladder_alpha": 19.79,
    "ladder_value_added": 1961.76,
    "status": "Beating"
  },
  {
    "date": "2026-06-25",
    "portfolio_value": 11761.88,
    "portfolio_roi": 18.65,
    "qqq_price": 716.38,
    "qqq_roi": 21.71,
    "qqq_value": 12065.28,
    "buy_hold_value": 9958.96,
    "buy_hold_roi": 0.46,
    "alpha": -3.06,
    "alpha_dollars": -303.4,
    "ladder_alpha": 18.19,
    "ladder_value_added": 1802.93,
    "status": "Lagging"
  },
  {
    "date": "2026-06-26",
    "portfolio_value": 11645.91,
    "portfolio_roi": 17.48,
    "qqq_price": 706.52,
    "qqq_roi": 20.04,
    "qqq_value": 11899.22,
    "buy_hold_value": 9909.92,
    "buy_hold_roi": -0.03,
    "alpha": -2.56,
    "alpha_dollars": -253.31,
    "ladder_alpha": 17.51,
    "ladder_value_added": 1735.99,
    "status": "Lagging"
  },
  {
    "date": "2026-06-29",
    "portfolio_value": 11831.59,
    "portfolio_roi": 19.35,
    "qqq_price": 724.08,
    "qqq_roi": 23.02,
    "qqq_value": 12194.96,
    "buy_hold_value": 9945.06,
    "buy_hold_roi": 0.32,
    "alpha": -3.67,
    "alpha_dollars": -363.37,
    "ladder_alpha": 19.03,
    "ladder_value_added": 1886.53,
    "status": "Lagging"
  },
  {
    "date": "2026-06-30",
    "portfolio_value": 11888.94,
    "portfolio_roi": 19.93,
    "qqq_price": 736.4,
    "qqq_roi": 25.11,
    "qqq_value": 12402.46,
    "buy_hold_value": 9993.69,
    "buy_hold_roi": 0.81,
    "alpha": -5.18,
    "alpha_dollars": -513.52,
    "ladder_alpha": 19.12,
    "ladder_value_added": 1895.25,
    "status": "Lagging"
  },
  {
    "date": "2026-07-01",
    "portfolio_value": 11956.4,
    "portfolio_roi": 20.61,
    "qqq_price": 725.17,
    "qqq_roi": 23.2,
    "qqq_value": 12213.32,
    "buy_hold_value": 9949.35,
    "buy_hold_roi": 0.37,
    "alpha": -2.59,
    "alpha_dollars": -256.92,
    "ladder_alpha": 20.25,
    "ladder_value_added": 2007.05,
    "status": "Lagging"
  },
  {
    "date": "2026-07-02",
    "portfolio_value": 11910.94,
    "portfolio_roi": 20.15,
    "qqq_price": 712.6,
    "qqq_roi": 21.07,
    "qqq_value": 12001.62,
    "buy_hold_value": 9804.68,
    "buy_hold_roi": -1.09,
    "alpha": -0.91,
    "alpha_dollars": -90.68,
    "ladder_alpha": 21.25,
    "ladder_value_added": 2106.26,
    "status": "Lagging"
  },
  {
    "date": "2026-07-06",
    "portfolio_value": 11995.71,
    "portfolio_roi": 21.01,
    "qqq_price": 722.82,
    "qqq_roi": 22.81,
    "qqq_value": 12173.74,
    "buy_hold_value": 9847.86,
    "buy_hold_roi": -0.66,
    "alpha": -1.8,
    "alpha_dollars": -178.03,
    "ladder_alpha": 21.67,
    "ladder_value_added": 2147.85,
    "status": "Lagging"
  },
  {
    "date": "2026-07-07",
    "portfolio_value": 11964.03,
    "portfolio_roi": 20.69,
    "qqq_price": 709.43,
    "qqq_roi": 20.53,
    "qqq_value": 11948.23,
    "buy_hold_value": 9860.54,
    "buy_hold_roi": -0.53,
    "alpha": 0.16,
    "alpha_dollars": 15.8,
    "ladder_alpha": 21.22,
    "ladder_value_added": 2103.49,
    "status": "Beating"
  },
  {
    "date": "2026-07-08",
    "portfolio_value": 12203.13,
    "portfolio_roi": 23.1,
    "qqq_price": 711.44,
    "qqq_roi": 20.87,
    "qqq_value": 11982.08,
    "buy_hold_value": 9928.38,
    "buy_hold_roi": 0.15,
    "alpha": 2.23,
    "alpha_dollars": 221.05,
    "ladder_alpha": 22.95,
    "ladder_value_added": 2274.75,
    "status": "Beating"
  },
  {
    "date": "2026-07-09",
    "portfolio_value": 13017.99,
    "portfolio_roi": 31.32,
    "qqq_price": 723.28,
    "qqq_roi": 22.88,
    "qqq_value": 12181.49,
    "buy_hold_value": 10093.61,
    "buy_hold_roi": 1.82,
    "alpha": 8.44,
    "alpha_dollars": 836.5,
    "ladder_alpha": 29.5,
    "ladder_value_added": 2924.38,
    "status": "Beating"
  }
]

# V55 cash-flow-aware performance endpoint for 2026-07-10.
QQQ_END_PRICE=725.54
qqq_twr=((QQQ_END_PRICE/QQQ_BENCHMARK['start_price'])-1)*100
benchmark_row={
    'date':'2026-07-10',
    'portfolio_value':round(account_total,2),
    'portfolio_roi':round(twr,4),
    'personal_roi':round(personal_roi,4),
    'qqq_price':QQQ_END_PRICE,
    'qqq_roi':round(qqq_twr,4),
    'qqq_value':round(BASELINE*(1+qqq_twr/100),2),
    'buy_hold_value':round(BASELINE*(1+QQQ_BENCHMARK.get('buy_hold_return_pct',0)/100),2),
    'buy_hold_roi':round(QQQ_BENCHMARK.get('buy_hold_return_pct',0),4),
    'alpha':round(twr-qqq_twr,4),
    'alpha_dollars':round(BASELINE*((twr-qqq_twr)/100),2),
    'ladder_alpha':round(twr-QQQ_BENCHMARK.get('buy_hold_return_pct',0),4),
    'ladder_value_added':round(BASELINE*((twr-QQQ_BENCHMARK.get('buy_hold_return_pct',0))/100),2),
    'status':'Beating' if twr>=qqq_twr else 'Lagging'
}
QQQ_BENCHMARK['replay_series']=[r for r in QQQ_BENCHMARK.get('replay_series',[]) if r.get('date')!='2026-07-10']+[benchmark_row]
QQQ_BENCHMARK.update({
    'end_date':'2026-07-10','end_price':QQQ_END_PRICE,'return_pct':qqq_twr,
    'portfolio_return_pct':twr,'personal_roi_pct':personal_roi,
    'alpha_pct':twr-qqq_twr,'status':benchmark_row['status'],
    'capital_ledger':capital_ledger,
    'notes':'3.53.0 uses cash-flow-segmented time-weighted return and validated sell ladders. The $5,055.52 contribution is excluded from performance.'
})

# Stock-specific ladder generation.
def buy_levels(sym, price):
    if price<=0 or sym in ['NVDA','AMZN','ARM','BAH']: return []
    if sym=='SPCX':
        return [('Buy Zone 1', round(price*.97), 'Add only on weakness'),('Buy Zone 2', round(price*.92), 'Strong add zone'),('Review Add', round(price*.85), 'Manual review')]
    if sym in ['ASML','CRWD','AMD']:
        return [('Seed Add', round(price*.985), 'Small incubator add'),('Add On', round(price*.965), 'Pullback add'),('Final Add', round(price*.93), 'Only if thesis intact')]
    return [('First Entry', round(price*.985), 'Limit buy'),('Add On', round(price*.965), 'Limit buy'),('Final Add', round(price*.945), 'Limit buy')]

def sell_levels(sym, price, qty, avg):
    if sym=='NVDA': return [('Trim 1',214,3,'Reduce concentration'),('Trim 2',220,4,'Harvest weak leader'),('Harvest',226,5,'Reallocate capital')]
    if sym=='AMZN':
        q=qty or 0
        # Sell ladders must harvest into strength, never below the latest market price.
        # Keep the first rung at least 1.5% above market and the second at least 4% above.
        first=round(price*1.015,2) if price>0 else 249.00
        second=round(price*1.04,2) if price>0 else 255.00
        if second <= first:
            second=round(first*1.02,2)
        return [('40% Exit',first,round(q*.4,3),'Validated harvest rung: at least 1.5% above market'),('60% Exit',second,round(q*.6,3),'Complete exit only into additional strength')]
    if sym=='BAH':
        q=qty or 0
        return [('Transition 1',64,round(q*.25,3),'Legacy RSU staged exit'),('Transition 2',66,round(q*.25,3),'Recycle into LadderIQ leaders'),('Transition 3',68,round(q*.25,3),'Continue concentration reduction'),('Final Review',72,round(q*.25,3),'Review full transition near target zone')]
    if sym=='SPCX':
        cost=avg or price
        return [('+50% Review', round(cost*1.5), qty, 'Review only'),('+100% Review', round(cost*2), qty, 'Consider capital recovery')]
    if sym=='ARM': return []
    if price<=0: return []
    if sym in ['ASML','CRWD','AMD']:
        return [('Review 1',round(price*1.08), qty*.33 if qty else 0, 'Review, not auto-sell'),('Review 2',round(price*1.15), qty*.33 if qty else 0, 'Scale only if needed')]
    return [('Trim 1',round(price*1.025), qty*.33 if qty else 0, 'Partial profit'),('Trim 2',round(price*1.05), qty*.33 if qty else 0, 'Lock gains'),('Harvest',round(price*1.075), qty*.34 if qty else 0, 'Full harvest')]

def budget_for(sym):
    weights={'TSM':.22,'PANW':.20,'ANET':.16,'ASML':.12,'CRWD':.10,'AMD':.10,'SPCX':.05}
    return deployable*weights.get(sym,0)

for st in stocks:
    st['buy']=[]; st['sell']=[]
    b=buy_levels(st['symbol'], st['price']); bud=budget_for(st['symbol'])
    if b:
        splits=[.5,.3,.2] if len(b)==3 else [1]
        for i,(label,price,note) in enumerate(b):
            alloc=bud*(splits[i] if i<len(splits) else 1/len(b))
            sh=alloc/price if price else 0
            st['buy'].append({'level':i+1,'label':label,'price':price,'allocation':alloc,'shares':sh,'note':note})
    for i,(label,price,sh,note) in enumerate(sell_levels(st['symbol'], st['price'], st['quantity'], st.get('avg_cost',0))):
        proceeds=(price or 0)*(sh or 0)
        st['sell'].append({'level':i+1,'label':label,'price':price,'shares':sh,'proceeds':proceeds,'note':note})

# Ladder QA: marketable sell limits are invalid unless explicitly approved.
# AMZN uses a 1.5% minimum harvest distance; all other ordinary sell ladders
# must at minimum remain above the latest market price.
for st in stocks:
    current=float(st.get('price') or 0)
    if current <= 0:
        continue
    for rung in st.get('sell',[]):
        sell_price=float(rung.get('price') or 0)
        if sell_price <= current:
            raise ValueError(f"Invalid sell ladder for {st['symbol']}: {sell_price} is not above current price {current}")
    if st.get('symbol') == 'AMZN' and st.get('sell'):
        minimum=round(current*1.015,2)
        if float(st['sell'][0]['price']) < minimum:
            raise ValueError(f"Invalid AMZN first sell rung: {st['sell'][0]['price']} is below validated minimum {minimum}")

group_meta={
 'Core Compounders': {'num':1,'color':'blue','target':'40–50%','desc':'Best-in-class leaders'},
 'Tactical Compounders': {'num':2,'color':'green','target':'20–40%','desc':'High-growth tactical leaders'},
 'Growth Engine': {'num':3,'color':'purple','target':'10–20%','desc':'Approved incubators'},
 'Special Situations': {'num':4,'color':'orange','target':'5–10%','desc':'Unique / event-driven'},
 'Legacy Holdings': {'num':5,'color':'red','target':'0–5%','desc':'RSUs / inherited / non-system positions'},
 'Watch List': {'num':6,'color':'gray','target':'0%','desc':'Monitor only'},
}

active_holdings = [s['symbol'] for s in stocks if s.get('quantity',0) > 0 and s.get('value',0) > 0]
approved_universe = [s['symbol'] for s in stocks if s['symbol'] not in ['ARM','BAH']]
watch_only = [s['symbol'] for s in stocks if s.get('status') == 'Watch Only']
legacy_holdings = [s['symbol'] for s in stocks if s['group'] == 'Legacy Holdings']

html_data=json.dumps({'stocks':stocks,'active_holdings':active_holdings,'approved_universe':approved_universe,'watch_only':watch_only,'legacy_holdings':legacy_holdings,'benchmark':QQQ_BENCHMARK,'metrics':{'account_total':account_total,'cash':cash,'pending':pending,'effective_cash':effective_cash,'deployable':deployable,'roi':roi,'personal_roi':personal_roi,'twr':twr,'net_gain':net_gain,'total_contributions':TOTAL_CONTRIBUTIONS,'new_contribution':NEW_CONTRIBUTION,'capital_ledger':capital_ledger,'today_pl':today_pl,'today_pl_pct':today_pl_pct,'baseline':BASELINE,'version':VERSION,'ladder_for':LADDER_FOR,'data_as_of':DATA_AS_OF},'groups':group_meta}, ensure_ascii=False)

css=r'''

:root{--bg:#07111d;--panel:#0c1726;--panel2:#101d2e;--line:#1e344d;--ink:#ecf5ff;--muted:#8ea4bc;--blue:#1e88ff;--green:#37d353;--red:#ff4d4d;--yellow:#ffbf2f;--purple:#b15cff;--orange:#ff9f1a;--gray:#8290a2}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 25% 0%,#10213a,#050b13 42%,#03070d);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}.app{display:grid;grid-template-columns:300px 1fr;gap:18px;padding:14px;min-height:100vh}.sidebar{background:rgba(12,23,38,.92);border:1px solid var(--line);border-radius:14px;padding:12px;height:calc(100vh - 28px);position:sticky;top:14px;overflow:auto}.brand{font-size:25px;font-weight:900;display:flex;align-items:center;gap:8px;white-space:nowrap;min-width:0}.brand-name{white-space:nowrap;display:inline-block}.brand .icon{flex:0 0 auto}.brand .green{color:#4fe36b}.version{font-size:13px;border:1px solid #1e88ff;color:#5fb5ff;padding:3px 8px;border-radius:6px;margin-left:auto}.subtitle{color:var(--muted);font-size:13px;margin:4px 0 18px 36px;white-space:nowrap}.decision-mini{border:1px solid var(--line);border-radius:10px;padding:12px;margin-bottom:14px;background:#081320}.decision-mini h3{margin:0 0 8px;font-size:14px}.search{display:flex;gap:8px;margin:12px 0}.search input{width:100%;background:#07111d;border:1px solid var(--line);border-radius:8px;color:var(--ink);padding:10px}.group{border:1px solid var(--line);border-radius:11px;margin:10px 0;overflow:hidden}.group-head{padding:10px 12px;font-weight:900;display:flex;justify-content:space-between;align-items:center;background:#0b1625}.group-head small{display:block;color:var(--muted);font-weight:600;margin-top:3px}.g-blue{border-color:#165aa8}.g-blue .group-head{color:#5fb5ff}.g-green{border-color:#238b3b}.g-green .group-head{color:#65e879}.g-purple{border-color:#7f3fc2}.g-purple .group-head{color:#ce94ff}.g-orange{border-color:#b96900}.g-orange .group-head{color:#ffb84a}.g-red{border-color:#a82424}.g-red .group-head{color:#ff6d6d}.g-gray{border-color:#586579}.g-gray .group-head{color:#b7c1cf}.stock-nav{display:grid;grid-template-columns:1fr auto auto;gap:7px;align-items:center;padding:9px 10px;border-top:1px solid rgba(255,255,255,.06);cursor:pointer}.stock-nav:hover,.stock-nav.active{background:#10243a}.sym{font-weight:900}.company-small{color:var(--muted);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pill{font-size:12px;background:#123a62;border:1px solid #265e91;border-radius:7px;padding:3px 7px}.trend{font-weight:900}.trend.up{color:var(--green)}.trend.lateral{color:var(--yellow)}.trend.down{color:var(--red)}.main{min-width:0}.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:14px}.kpi{background:linear-gradient(180deg,#0d1929,#08111e);border:1px solid var(--line);border-radius:12px;padding:14px}.kpi .label{color:#b8c8dc;font-size:12px;text-transform:uppercase}.kpi .value{font-size:25px;font-weight:900;margin-top:8px}.positive{color:var(--green)}.negative{color:var(--red)}.progress{height:12px;background:#04101c;border-radius:999px;overflow:hidden;margin-top:12px}.bar{height:100%;background:linear-gradient(90deg,#39d353,#a8ff60);border-radius:999px}.decision{background:rgba(12,23,38,.9);border:1px solid var(--line);border-radius:13px;padding:14px;margin-bottom:14px}.decision-title{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}.decision-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.dec-card{border-radius:12px;border:1px solid var(--line);padding:16px;background:#091523}.dec-card.buy{border-color:#24903a;background:linear-gradient(135deg,rgba(18,95,34,.45),rgba(9,21,35,.9))}.dec-card.sell{border-color:#b62626;background:linear-gradient(135deg,rgba(114,26,35,.5),rgba(9,21,35,.9))}.dec-card.watch{border-color:#b47a00;background:linear-gradient(135deg,rgba(117,80,0,.45),rgba(9,21,35,.9))}.dec-card h3{margin:0 0 8px;text-transform:uppercase}.dec-symbol{font-size:28px;font-weight:900}.scorebig{float:right;font-size:24px;font-weight:900}.detail{background:rgba(12,23,38,.9);border:1px solid var(--line);border-radius:13px;padding:0;overflow:hidden}.stock-hero{display:grid;grid-template-columns:1.2fr 1.4fr auto;gap:16px;padding:20px;border-bottom:1px solid var(--line);align-items:center}.stock-title{font-size:32px;font-weight:900}.tags span{display:inline-block;margin-right:6px;margin-top:8px;padding:5px 9px;border-radius:6px;background:#0b3b71;color:#80c7ff;font-size:12px;font-weight:900}.metrics-row{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}.mini-metric{border-left:1px solid var(--line);padding-left:12px}.mini-metric small{color:var(--muted);display:block}.mini-metric b{font-size:20px}.actions button{background:#0a3768;color:white;border:1px solid #2362a2;border-radius:7px;padding:8px 10px;margin-left:6px}.tabs{display:flex;gap:26px;padding:0 20px;border-bottom:1px solid var(--line)}.tab{padding:14px 0;color:var(--muted);font-weight:800}.tab.active{color:#48a7ff;border-bottom:2px solid #48a7ff}.content{display:grid;grid-template-columns:1fr 1fr 300px;gap:12px;padding:14px}.ladder{border:1px solid var(--line);border-radius:10px;background:#081320;overflow:hidden}.ladder h3{margin:0;padding:12px 14px;border-bottom:1px solid var(--line)}.ladder.buy h3{color:var(--green)}.ladder.sell h3{color:var(--red)}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid rgba(255,255,255,.06);text-align:left;font-size:13px}th{color:var(--muted);font-size:11px;text-transform:uppercase}.levelbox{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:7px;background:#164f26;color:#d7ffd9;font-weight:900}.sell .levelbox{background:#5a1d23;color:#ffd8d8}.price{font-size:20px;font-weight:900}.limit{font-size:11px;color:#69e76e}.sell .limit{color:#ff7777}.side-panel{display:flex;flex-direction:column;gap:12px}.box{background:#081320;border:1px solid var(--line);border-radius:10px;padding:14px}.box h3{margin:0 0 12px}.profile-row{display:grid;grid-template-columns:1fr 120px 42px;gap:8px;align-items:center;margin:9px 0}.meter{height:9px;background:#0d2238;border-radius:99px;overflow:hidden}.meter span{display:block;height:100%;background:var(--green)}.lower{display:grid;grid-template-columns:1fr 1fr 1.2fr 1fr;gap:12px;padding:0 14px 14px}.chart{height:130px;border-radius:9px;background:linear-gradient(180deg,rgba(57,211,83,.12),rgba(57,211,83,.02));border:1px solid rgba(57,211,83,.25);position:relative;overflow:hidden}.chart:after{content:'';position:absolute;left:15px;right:15px;bottom:22px;height:65px;background:linear-gradient(135deg,transparent 0 8%,rgba(57,211,83,.8) 9% 10%,transparent 11% 22%,rgba(57,211,83,.8) 23% 24%,transparent 25% 42%,rgba(57,211,83,.8) 43% 44%,transparent 45% 58%,rgba(57,211,83,.8) 59% 60%,transparent 61% 78%,rgba(57,211,83,.8) 79% 80%,transparent 81%)}.footer-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;margin-top:12px}.small-card{background:rgba(12,23,38,.9);border:1px solid var(--line);border-radius:11px;padding:12px;min-width:0}.small-card p{font-size:11px;line-height:1.25}.small-card h3{font-size:14px}.small-card .bench-big{font-size:26px;font-weight:900}.small-card .bench-line{display:flex;justify-content:space-between;gap:8px;font-size:12px;margin:6px 0}.small-card h3{margin:0 0 10px}.rank-row{display:grid;grid-template-columns:26px 1fr auto;gap:8px;margin:7px 0}.footer{color:var(--muted);font-size:12px;text-align:center;margin:14px}.hidden{display:none!important}.health-score{font-size:34px;font-weight:900;margin:4px 0}.health-bars{display:grid;gap:8px;margin-top:10px}.health-line{display:grid;grid-template-columns:120px 1fr 42px;gap:8px;align-items:center;font-size:12px}.health-meter{height:9px;background:#0d2238;border-radius:99px;overflow:hidden}.health-meter span{display:block;height:100%;background:linear-gradient(90deg,#39d353,#a8ff60)}.callout{margin-top:10px;padding:8px;border:1px solid var(--line);border-radius:8px;background:#081320}.callout b{display:block;margin-bottom:4px}.warning-text{color:var(--yellow)}.bench-range{width:100%;accent-color:#37d353;margin:6px 0}.bench-date-row{display:flex;justify-content:space-between;gap:6px;color:var(--muted);font-size:10px}.bench-note{font-size:10px;color:var(--muted);line-height:1.2;margin-top:3px}.bench-microgrid{display:grid;grid-template-columns:1fr 1fr;gap:4px 8px;margin-top:5px}.bench-micro{font-size:10px;color:var(--muted);min-width:0}.bench-micro b{display:block;color:var(--ink);font-size:11px;white-space:nowrap}.bench-micro b.positive{color:var(--green)}.bench-micro b.negative{color:var(--red)}.bench-sub{font-size:10px;color:var(--muted);margin-top:-6px;margin-bottom:3px}.bench-period{font-size:10px;color:var(--muted);display:flex;justify-content:space-between;margin:3px 0}.bench-alpha-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.02em}@media(max-width:1200px){.app{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.kpis,.decision-grid,.content,.lower,.footer-grid{grid-template-columns:1fr}.stock-hero{grid-template-columns:1fr}.metrics-row{grid-template-columns:repeat(2,1fr)}}

'''

script=r'''
const DATA = __DATA__;
const fmtMoney = v => '$' + Number(v||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
const fmtPct = v => Number(v||0).toFixed(2)+'%';
const fmtSh = v => Number(v||0).toFixed(3).replace(/\.0+$/,'').replace(/(\.\d*?)0+$/,'$1');
function trendClass(t){return (t||'').toLowerCase()==='up'?'up':((t||'').toLowerCase()==='down'?'down':'lateral')}
function trendIcon(t){return (t||'').toLowerCase()==='up'?'↑':((t||'').toLowerCase()==='down'?'↓':'→')}
function kpi(){const m=DATA.metrics; document.getElementById('kpis').innerHTML=`
 <div class="kpi"><div class="label">Account Total</div><div class="value">${fmtMoney(m.account_total)}</div><small>Market value</small></div>
 <div class="kpi"><div class="label">Effective Cash</div><div class="value">${fmtMoney(m.effective_cash)}</div><small>Raw cash + pending</small></div>
 <div class="kpi"><div class="label">Buying Power</div><div class="value">${fmtMoney(m.deployable)}</div><small>After 15% reserve</small></div>
 <div class="kpi"><div class="label">Strategy Return (TWR)</div><div class="value ${m.twr>=0?'positive':'negative'}">${m.twr>=0?'+':''}${fmtPct(m.twr)}</div><small>Personal ROI ${m.personal_roi>=0?'+':''}${fmtPct(m.personal_roi)} · Net gain ${m.net_gain>=0?'+':''}${fmtMoney(m.net_gain)}</small></div>
 <div class="kpi"><div class="label">Today's P/L</div><div class="value ${m.today_pl>=0?'positive':'negative'}">${m.today_pl>=0?'+':''}${fmtMoney(m.today_pl)}</div><small>${m.today_pl>=0?'+':''}${fmtPct(m.today_pl_pct)}</small></div>
 <div class="kpi"><div class="label">Progress to 100% Goal</div><div class="value">${fmtPct(m.roi)}</div><div class="progress"><div class="bar" style="width:${Math.min(100,Math.max(0,m.roi))}%"></div></div></div>`;}
function sidebar(){const groups=DATA.groups; const by={}; DATA.stocks.forEach(s=>{(by[s.group]??=[]).push(s)}); let html='<div class=\"brand\"><span class=\"icon\">📈</span><span class=\"brand-name\">LadderIQ</span><span class=\"version\">'+DATA.metrics.version+'</span></div><div class="subtitle">Portfolio Command Center</div><div class="decision-mini"><h3>✨ Decision Center</h3><div>Your top 3 priorities for '+DATA.metrics.ladder_for+'</div><button style="margin-top:10px;background:#09294b;border:1px solid #2362a2;color:#80c7ff;border-radius:7px;padding:8px 10px">View All Opportunities</button></div><h3>Portfolio Hierarchy</h3><div style="color:var(--muted);font-size:11px;margin-top:-4px;margin-bottom:8px">Sidebar number = Opportunity Score, not business quality.</div><div class="search"><input placeholder="Search symbols..." oninput="filterStocks(this.value)"></div>';
 Object.keys(groups).forEach(g=>{const meta=groups[g]; const arr=by[g]||[]; html+=`<div class="group g-${meta.color}"><div class="group-head"><div>${meta.num} ${g}<small>Target: ${meta.target} · ${arr.length} Holdings</small></div><div>⌄</div></div>`; arr.forEach(s=>{html+=`<div class="stock-nav" data-symbol="${s.symbol}" onclick="selectStock('${s.symbol}')"><div><div class="sym">${s.symbol}</div><div class="company-small">${s.company}</div></div><span class="pill" title="Opportunity Score: where the next dollar should go today">${Math.round(s.opportunity ?? s.leadership)}</span><span class="trend ${trendClass(s.trend)}">${s.trend}</span></div>`}); html+='</div>'});
 html+=`<div class="box"><small>Data as of: ${DATA.metrics.data_as_of}</small><br><small>Next Ladder: <b>${DATA.metrics.ladder_for}</b></small></div>`; document.getElementById('sidebar').innerHTML=html;}
function decision(){const buy=DATA.stocks.find(s=>s.symbol==='ASML'); const sell=DATA.stocks.find(s=>s.symbol==='NVDA'); const watch=DATA.stocks.find(s=>s.symbol==='AMZN'); document.getElementById('decision').innerHTML=`<div class="decision-title"><div><b>Decision Center</b> <span style="color:var(--muted);margin-left:12px">Today's top priorities</span></div><a style="color:#58b5ff">View All Signals →</a></div><div class="decision-grid">
 <div class="dec-card buy"><h3>🛒 Buy Today <span class="scorebig">98/100</span></h3><div class="dec-symbol">${buy.symbol}</div><div>${buy.company}</div><p>Why: strongest approved incubator; pullback + opportunity + quality setup.</p></div>
 <div class="dec-card sell"><h3>🎯 Sell Today <span class="scorebig">92/100</span></h3><div class="dec-symbol">${sell.symbol}</div><div>${sell.company}</div><p>Why: over 50% of portfolio, in harvest mode, reduce concentration.</p></div>
 <div class="dec-card watch"><h3>👁 Watch Closely <span class="scorebig">72/100</span></h3><div class="dec-symbol">${watch.symbol}</div><div>${watch.company}</div><p>Why: weak momentum; could continue toward full rotation exit.</p></div>
 </div>`;}
function ladderRows(levels,type){return levels.map(x=>`<tr><td><span class="levelbox">${x.level}</span></td><td><div class="price">${fmtMoney(x.price)}</div><div class="limit">Limit ${type==='buy'?'Buy':'Sell'}</div></td><td>${type==='buy'?fmtMoney(x.allocation):fmtPct(x.shares?33:0)}</td><td>${fmtSh(x.shares)}</td><td>${type==='buy'?'Waiting':fmtMoney(x.proceeds)}</td><td>${x.note||''}</td></tr>`).join('') || '<tr><td colspan="6">No ladder for this side.</td></tr>'}
function selectStock(sym){const s=DATA.stocks.find(x=>x.symbol===sym)||DATA.stocks[0]; document.querySelectorAll('.stock-nav').forEach(el=>el.classList.toggle('active',el.dataset.symbol===sym)); const pl=s.total_pl||0; document.getElementById('detail').innerHTML=`
 <div class="stock-hero"><div><div class="stock-title">${s.symbol}</div><div style="color:var(--muted)">${s.company}</div><div class="tags"><span>${s.role}</span><span>${s.group}</span></div></div><div class="metrics-row"><div class="mini-metric"><small>Opportunity</small><b>${Math.round(s.opportunity ?? s.leadership)}</b></div><div class="mini-metric"><small>Trend</small><b class="trend ${trendClass(s.trend)}">${trendIcon(s.trend)} ${s.trend}</b></div><div class="mini-metric"><small>Business Quality</small><b>${Math.round(s.business_quality ?? s.leadership)}</b></div><div class="mini-metric"><small>% Portfolio</small><b>${fmtPct(s.weight)}</b></div><div class="mini-metric"><small>Market Value</small><b>${fmtMoney(s.value)}</b></div></div><div class="actions"><button>Add Note</button><button>View Chart</button><button>Set Alert</button><div style="margin-top:12px"><small>Unrealized P/L</small><br><b class="${pl>=0?'positive':'negative'}">${pl>=0?'+':''}${fmtMoney(pl)}</b></div></div></div>
 <div class="tabs"><div class="tab active">Overview</div><div class="tab">Ladders</div><div class="tab">Analysis</div><div class="tab">Notes</div><div class="tab">Performance</div></div>
 <div class="content"><div class="ladder buy"><h3>Buy Ladder (${s.status}) <span style="float:right;color:var(--muted);font-size:13px">Budget: ${fmtMoney(s.buy.reduce((a,b)=>a+b.allocation,0))}</span></h3><table><thead><tr><th>Level</th><th>Price</th><th>Allocation</th><th>Shares</th><th>Status</th><th>Notes</th></tr></thead><tbody>${ladderRows(s.buy,'buy')}</tbody></table></div><div class="ladder sell"><h3>Sell Ladder / Review <span style="float:right;color:var(--muted);font-size:13px">Target: ${fmtMoney(s.sell.reduce((a,b)=>a+b.proceeds,0))}</span></h3><table><thead><tr><th>Level</th><th>Price</th><th>Trim</th><th>Shares</th><th>Proceeds</th><th>Notes</th></tr></thead><tbody>${ladderRows(s.sell,'sell')}</tbody></table></div><div class="side-panel"><div class="box"><h3>Score Breakdown</h3><div style="color:var(--muted);font-size:12px;margin-bottom:10px">Opportunity score is tactical. Business quality is long-term.</div>${['Relative Strength','Momentum','Price Structure','Capital Priority','Opportunity Score'].map((n,i)=>`<div class="profile-row"><span>${n}</span><div class="meter"><span style="width:${Math.max(10,Math.min(100,s.leadership-(i*2)))}%"></span></div><b>${Math.max(0,Math.round(s.leadership-(i*2)))}</b></div>`).join('')}</div><div class="box"><h3>Key Levels</h3><div>Current: <b style="float:right">${fmtMoney(s.price)}</b></div><div>Avg Cost: <b style="float:right">${fmtMoney(s.avg_cost)}</b></div><div>Shares: <b style="float:right">${fmtSh(s.quantity)}</b></div><div>Weight: <b style="float:right">${fmtPct(s.weight)}</b></div><div>Reason Owned: <b style="float:right">${s.own_reason || 'LadderIQ Selected'}</b></div><div class="callout"><b>Score Interpretation</b><span>${s.score_reason || 'Opportunity score controls today’s capital allocation.'}</span></div></div></div></div>
 <div class="lower"><div class="box"><h3>Technical Snapshot</h3><div>Price (AH) <b style="float:right">${fmtMoney(s.price)}</b></div><div>Trend <b class="trend ${trendClass(s.trend)}" style="float:right">${s.trend}</b></div><div>Opportunity <b style="float:right">${Math.round(s.opportunity ?? s.leadership)}</b></div><div>Business Quality <b style="float:right">${Math.round(s.business_quality ?? s.leadership)}</b></div></div><div class="box"><h3>Portfolio Health</h3><div class="health-score positive">91<small>/100</small></div><div class="positive">Excellent</div><div class="health-bars"><div class="health-line"><span>Opportunity</span><div class="health-meter"><span style="width:95%"></span></div><b>95</b></div><div class="health-line"><span>Diversification</span><div class="health-meter"><span style="width:84%"></span></div><b>84</b></div><div class="health-line"><span>Risk Mgmt</span><div class="health-meter"><span style="width:92%"></span></div><b>92</b></div><div class="health-line"><span>Cash Efficiency</span><div class="health-meter"><span style="width:78%"></span></div><b>78</b></div><div class="health-line"><span>Momentum</span><div class="health-meter"><span style="width:97%"></span></div><b>97</b></div></div><div class="callout"><b>Biggest Weakness</b><span class="warning-text">NVDA concentration remains high; harvest plan stays active.</span></div></div><div class="box"><h3>Capital Allocation Engine</h3><div>Deployable cash: <b>${fmtMoney(DATA.metrics.deployable)}</b></div><div class="progress"><div class="bar" style="width:86%"></div></div><small>Cash efficiency: Good</small></div><div class="box"><h3>Allocation & Risk</h3><div style="font-size:34px;font-weight:900">${fmtPct(s.weight)}</div><div>Risk Status: <b class="positive">${s.weight>40?'Watch':'Good'}</b></div></div></div>`;}
function renderBenchmarkCard(){
 const b=DATA.benchmark || {};
 const series=(b.replay_series && b.replay_series.length)?b.replay_series:(b.series || []).map(x=>({date:x.date, qqq_price:x.price, qqq_roi:((Number(x.price)/Number(b.start_price))-1)*100, portfolio_roi:Number(DATA.metrics.roi||0)}));
 const maxIdx=Math.max(0,series.length-1);
 const defaultIdx=maxIdx;
 const end=series[defaultIdx] || {date:b.end_date, qqq_roi:b.return_pct, portfolio_roi:DATA.metrics.roi, alpha:b.alpha_pct};
 const port=Number(end.portfolio_roi ?? DATA.metrics.roi ?? 0);
 const qret=Number(end.qqq_roi ?? b.return_pct ?? 0);
 const bh=Number(end.buy_hold_roi ?? 0);
 const ladder=Number(end.ladder_alpha ?? (port-bh));
 const alpha=Number(end.alpha ?? (port-qret));
 const qqqValue=Number(end.qqq_value ?? (Number(DATA.metrics.baseline||0)*(1+qret/100)));
 const alphaDollars=Number(end.alpha_dollars ?? (Number(DATA.metrics.baseline||0)*(alpha/100)));
 const ladderValue=Number(end.ladder_value_added ?? 0);
 return `<div class="small-card"><h3>Benchmark vs QQQ</h3><div class="bench-alpha-label">Alpha vs QQQ</div><div id="benchAlpha" class="bench-big ${alpha>=0?'positive':'negative'}">${alpha>=0?'+':''}${fmtPct(alpha)}</div><div class="bench-line"><span>Portfolio TWR</span><b id="benchPortfolio">${port>=0?'+':''}${fmtPct(port)}</b></div><div class="bench-line"><span>QQQ ROI</span><b id="benchQQQ">${qret>=0?'+':''}${fmtPct(qret)}</b></div><div class="bench-microgrid"><div class="bench-micro">Buy & Hold<b id="benchBuyHold">${bh>=0?'+':''}${fmtPct(bh)}</b></div><div class="bench-micro">LadderIQ Value<b id="benchLadderValue" class="${ladderValue>=0?'positive':'negative'}">${ladderValue>=0?'+':''}${fmtMoney(ladderValue)}</b></div><div class="bench-micro">Ladder Alpha<b id="benchLadderAlpha" class="${ladder>=0?'positive':'negative'}">${ladder>=0?'+':''}${fmtPct(ladder)}</b></div><div class="bench-micro">Personal ROI<b id="benchPersonalROI">${Number(end.personal_roi ?? DATA.metrics.personal_roi ?? 0)>=0?'+':''}${fmtPct(Number(end.personal_roi ?? DATA.metrics.personal_roi ?? 0))}</b></div></div><div class="bench-period"><span>Period</span><b><span>${b.start_date||''}</span> → <span id="benchEndDate">${end.date||''}</span></b></div><input id="benchSlider" class="bench-range" type="range" min="0" max="${maxIdx}" value="${defaultIdx}" oninput="updateBenchmark(this.value)"><div class="bench-note">Start locked at 2026-04-07. Drag end date. Portfolio, QQQ, Buy & Hold, and LadderIQ Value update together.</div></div>`;
}
function updateBenchmark(idx){
 const b=DATA.benchmark || {}; const series=(b.replay_series && b.replay_series.length)?b.replay_series:(b.series || []);
 const item=series[Number(idx)] || series[series.length-1] || {};
 const port=Number(item.portfolio_roi ?? DATA.metrics.roi ?? 0);
 const qret=Number(item.qqq_roi ?? (((Number(item.price||item.qqq_price)/Number(b.start_price))-1)*100) ?? 0);
 const bh=Number(item.buy_hold_roi ?? 0);
 const ladder=Number(item.ladder_alpha ?? (port-bh));
 const alpha=Number(item.alpha ?? (port-qret));
 const ladderValue=Number(item.ladder_value_added ?? 0);
 const personal=Number(item.personal_roi ?? DATA.metrics.personal_roi ?? port);
 const alphaDollars=Number(item.alpha_dollars ?? (Number(DATA.metrics.baseline||0)*(alpha/100)));
 const qqqValue=Number(item.qqq_value ?? (Number(DATA.metrics.baseline||0)*(1+qret/100)));
 const setText=(id,txt)=>{const el=document.getElementById(id); if(el)el.textContent=txt;};
 const setClass=(id,base,val)=>{const el=document.getElementById(id); if(el)el.className=(base?base+' ':'')+(val>=0?'positive':'negative');};
 setText('benchAlpha',(alpha>=0?'+':'')+fmtPct(alpha)); setClass('benchAlpha','bench-big',alpha);
 setText('benchPortfolio',(port>=0?'+':'')+fmtPct(port));
 setText('benchQQQ',(qret>=0?'+':'')+fmtPct(qret));
 setText('benchBuyHold',(bh>=0?'+':'')+fmtPct(bh));
 setText('benchLadderAlpha',(ladder>=0?'+':'')+fmtPct(ladder)); setClass('benchLadderAlpha','',ladder);
 setText('benchLadderValue',(ladderValue>=0?'+':'')+fmtMoney(ladderValue)); setClass('benchLadderValue','',ladderValue);
 setText('benchPersonalROI',(personal>=0?'+':'')+fmtPct(personal));
 setText('benchEndDate',item.date || '');
 setText('benchAlphaDollars',(alphaDollars>=0?'+':'')+fmtMoney(alphaDollars)); setClass('benchAlphaDollars','',alpha);
 setText('benchQQQValue',fmtMoney(qqqValue));
 setText('benchStatus',alpha>=0?'Beating':'Lagging'); setClass('benchStatus','',alpha);
}
function footer(){
 const opp=['PANW','ANET','CRWD','TSM','ASML'].filter(x=>DATA.stocks.find(s=>s.symbol===x));
 const strategic=['NVDA','TSM','ASML','PANW'].filter(x=>DATA.stocks.find(s=>s.symbol===x));
 const emerging=['DELL','SNOW','VRT','ARM','GOOGL'];
 document.getElementById('footergrid').innerHTML=`<div class="small-card"><h3>Portfolio Health</h3><div style="font-size:30px;font-weight:900">94<small>/100</small></div><div class="positive">Excellent</div><p style="color:var(--muted)">Opportunity score drives new capital. Business quality stays separate.</p></div>${renderBenchmarkCard()}<div class="small-card"><h3>Opportunity Ranking</h3>${opp.map((r,i)=>{const st=DATA.stocks.find(s=>s.symbol===r); return `<div class="rank-row"><b>${i+1}</b><span>${r}</span><span class="positive">${Math.round(st?.opportunity ?? st?.leadership ?? 0)}</span></div>`}).join('')}</div><div class="small-card"><h3>Strategic Leaders</h3>${strategic.map((r,i)=>{const st=DATA.stocks.find(s=>s.symbol===r); return `<div class="rank-row"><b>${i+1}</b><span>${r}</span><span>${Math.round(st?.business_quality ?? 0)}</span></div>`}).join('')}<p style="color:var(--muted)">Quality names; not always current buys.</p></div><div class="small-card"><h3>Watch / Emerging</h3>${emerging.map((r,i)=>`<div class="rank-row"><b>${i+1}</b><span>${r}</span><span>${i<2?'Attack':'Hold'}</span></div>`).join('')}</div><div class="small-card"><h3>Legacy Holdings</h3><div class="rank-row"><b>1</b><span>BAH</span><span>RSU</span></div><p style="color:var(--muted)">Exit zone $72–75. Risk review below $58–60. Proceeds convert to LadderIQ cash.</p></div>`;}
function filterStocks(q){q=(q||'').toUpperCase(); document.querySelectorAll('.stock-nav').forEach(el=>{el.style.display=el.dataset.symbol.includes(q)?'grid':'none'})}
kpi(); sidebar(); decision(); footer(); selectStock('TSM');

'''.replace('__DATA__', html_data)

html=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>LadderIQ {VERSION} Portfolio Command Center</title><style>{css}</style></head><body><div class="app"><aside id="sidebar" class="sidebar"></aside><main class="main"><section id="kpis" class="kpis"></section><section id="decision" class="decision"></section><section id="detail" class="detail"></section><section id="footergrid" class="footer-grid"></section><div class="footer">LadderIQ | {VERSION} | Data as of {DATA_AS_OF} | Next ladder: {LADDER_FOR}</div></main></div><script>{script}</script></body></html>'''

# reports/latestladder.html is the authoritative generated report.
REPORTS_DIR = ROOT / 'reports'
ARCHIVE_DIR = REPORTS_DIR / 'archive'
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
AUTHORITATIVE_REPORT = REPORTS_DIR / 'latestladder.html'
AUTHORITATIVE_REPORT.write_text(html, encoding='utf-8')

# Preserve a dated snapshot when the build has a valid data date.
archive_name = f"{DATA_AS_OF[:10]}.html" if re.match(r'\d{4}-\d{2}-\d{2}', DATA_AS_OF) else None
if archive_name:
    (ARCHIVE_DIR / archive_name).write_text(html, encoding='utf-8')

# Transitional compatibility copies for old shortcuts and integrations.
(ROOT / 'latestladder.html').write_text(html, encoding='utf-8')
(ROOT / 'index.html').write_text(html, encoding='utf-8')
readme=fr'''# LadderIQ {VERSION} — Tomorrow Ladder

Updated with the latest Fidelity files detected in the project folder.

## Correct PowerShell Workflow

```powershell
cd "C:\Users\mcdph\OneDrive\03 - LadderIQ Platform\04 - Development"
python .\import_fidelity_csv.py
python .\import_positions.py
python .\leadership_scanner.py
python .\build_ladder.py
start .\reports\latestladder.html
```

If `leadership_scanner.py` fails because `yfinance` is not installed, either install it:

```powershell
pip install yfinance
```

or skip that step and build using the latest existing `leadership_scores.json`:

```powershell
python .\build_ladder.py
start .\reports\latestladder.html
```

## CSV Auto-Detection

You no longer need to rename Fidelity exports. The scripts automatically select the newest matching files in the project folder:

- Account history: `Accounts_History*.csv` or `History_for_Account*.csv`
- Positions: `Portfolio_Positions*.csv`

Examples that now work without renaming:

- `Accounts_History.csv`
- `Accounts_History (1).csv`
- `Accounts_History (2).csv`
- `Accounts_History (3).csv`
- `History_for_Account_Z25686771.csv`
- `Portfolio_Positions_Jul-09-2026.csv`

If you need to force a specific history file:

```powershell
python .\import_fidelity_csv.py --csv "Accounts_History (3).csv"
```

If you need to force a specific positions file:

```powershell
python .\import_positions.py --csv "Portfolio_Positions_Jul-09-2026.csv"
```

## Build Script

Use `build_ladder.py`. The old version-specific build name (`build_v41.py`) has been removed.

Do not run `update_portfolio.py`; that file is not part of this system.

## {VERSION} Features

- Portfolio Command Center layout
- Decision Center: Buy Today / Sell Today / Watch Closely
- Left-side portfolio hierarchy
- Opportunity Score and Business Quality are separated.
- Legacy Holdings framework for RSUs / inherited / non-system positions.
- Benchmark vs QQQ card uses cash-flow-segmented TWR and keeps Personal ROI separate.
- Capital ledger records the $5,055.52 external contribution without treating it as gain.
- Adaptive learning records NVDA and AMZN manual ladder overrides for future rule proposals.
- META remains removed.

## Latest Build Inputs

- Positions file: `{pos_file}`
- Account Total: {fmt_money(account_total)}
- Effective Cash: {fmt_money(effective_cash)}
- ROI Since Inception: {roi:.2f}%
- Next ladder: {LADDER_FOR}
'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')
# overwrite generate_ladder.py with generator copy that is portable (adjust ROOT to cwd)
gen=Path(__file__).read_text(encoding='utf-8').replace("ROOT=Path(__file__).resolve().parent","ROOT=Path(__file__).resolve().parent")
(ROOT/'generate_ladder.py').write_text(gen,encoding='utf-8')
# validation no stale visible bad versions in html/readme
bad=[]
validation_files = [ROOT/'index.html', ROOT/'latestladder.html', ROOT/'reports'/'latestladder.html', ROOT/'README.md']
for path in validation_files:
    txt=path.read_text(encoding='utf-8')
    f=str(path.relative_to(ROOT))
    for v in ['V24','V29','V30','V31','V32','V33','V34','V35','V36','V37','V38','V39','V40']:
        if v in txt: bad.append((f,v))
if bad:
    print('STALE_VERSION_FAIL',bad); raise SystemExit(1)
print(json.dumps({'version':VERSION,'account_total':account_total,'effective_cash':effective_cash,'roi':roi,'pos_file':pos_file},indent=2))
