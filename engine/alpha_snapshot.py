#!/usr/bin/env python3
"""OKX research-only alpha data snapshot: NO TRADING, NO SIGNAL SCORING."""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from engine.alpha_core import BARS, COINS, parse_okx_rows, relative_close

URL='https://www.okx.com/api/v5/market/history-candles'
OUT=Path('artifacts/alpha_research_snapshot.json')

def fetch(inst,bar):
    url=URL+'?'+urllib.parse.urlencode({'instId':inst,'bar':bar,'limit':100})
    req=urllib.request.Request(url, headers={'User-Agent':'alpha-research-only/0.1','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=18) as response:
        if response.status!=200: raise RuntimeError('HTTP_'+str(response.status))
        return json.loads(response.read(1_500_000))

def main():
    now=int(time.time())
    report={'version':'alpha-0.1-candidate','timestamp_utc':datetime.fromtimestamp(now,timezone.utc).isoformat(),
        'repository':os.getenv('GITHUB_REPOSITORY'), 'run_id':os.getenv('GITHUB_RUN_ID'),
        'research_only':True,'trading_enabled':False,'signals_enabled':False,
        'release_6_0_0_approved':False,'scores_computed':False,'signals':[],
        'source':'OKX Spot','quote':'USDT','timeframes':{}, 'ready_for_score_engine':False,
        'continuous_freshness_proven':False}
    cached={}
    for tf,(_,bar) in BARS.items():
        summary={}
        for asset in ('BTC',)+COINS:
            try:
                payload=fetch(asset+'-USDT',bar)
                cached[(tf,asset)]=parse_okx_rows(payload,tf,now)
                summary[asset]={'status':'RECEIVED','closed_candles':len(cached[(tf,asset)])}
            except Exception as exc:
                cached[(tf,asset)]={}
                summary[asset]={'status':'BLOCKED','error':str(exc)[:160]}
        relative={}
        for asset in COINS:
            try: relative[asset]=relative_close(cached[(tf,asset)],cached[(tf,'BTC')],tf,now)
            except Exception as exc: relative[asset]={'status':'BLOCKED','reason':type(exc).__name__+': '+str(exc)[:120]}
        report['timeframes'][tf]={'collection':summary,'relative_to_btc':relative}
    report['relative_close_valid_count']=sum(item['status']=='VALIDATED_RELATIVE_CLOSE' for v in report['timeframes'].values() for item in v['relative_to_btc'].values())
    report['relative_close_total']=len(BARS)*len(COINS)
    report['outcome']='RESEARCH_DATA_ONLY'
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('Saved',OUT,report['relative_close_valid_count'],'/',report['relative_close_total'])

if __name__=='__main__':main()
