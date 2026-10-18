"""Research only; 40 markets; no trading and no signals."""
import json,os,time
from pathlib import Path
from datetime import datetime,timezone
from engine.alpha_core import COINS,BARS
from engine.alpha_sma_v04 import collect_history
from engine.alpha_multir_v10 import simulate

def main():
    now=int(time.time())
    out={'version':'alpha-1.0-multi-rr-structural-research','run_id':os.getenv('GITHUB_RUN_ID'),
         'timestamp_utc':datetime.fromtimestamp(now,timezone.utc).isoformat(),
         'research_only':True,'trading_enabled':False,'signals_enabled':False,'signals':[],
         'release_6_0_0_approved':False,'continuous_freshness_proven':False,
         'backtest_completed':False,'backtest_scope':'IN_SAMPLE_EXPLORATORY',
         'markets':{},'totals':{}}
    for tf in BARS:
        out['markets'][tf]={}
        for coin in COINS:
            try:
                data=collect_history(coin+'-USDT',tf,now)
                out['markets'][tf][coin]=simulate(data,tf,now)
            except Exception as ex:
                out['markets'][tf][coin]={'status':'BLOCKED','reason':type(ex).__name__+':'+str(ex)[:160], 'signal_authorized':False}
    allv=[v for block in out['markets'].values() for v in block.values()]
    out['totals']={'expected_markets':40,'computed':sum(x['status']=='INSAMPLE_RESEARCH_SIMULATION' for x in allv),
                   'blocked':sum(x['status']=='BLOCKED' for x in allv),
                   'candidate_events':sum(x.get('candidate_events',0) for x in allv),'signals':0}
    p=Path('artifacts/alpha_multir_v10.json');p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
    print(out['totals'])
    if out['totals']['blocked']:raise SystemExit('BLOCKED MARKETS')
if __name__=='__main__':main()
