#!/usr/bin/env python3
"""Read-only research alpha diagnostics against OKX spot. Does not alter core engine."""
import json,os,sys,time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from engine.alpha_core import BARS,COINS,parse_okx_rows,relative_close
from engine.alpha_snapshot import fetch
from engine.alpha_diagnostics import diagnose

OUT=Path('artifacts/alpha_diagnostics_v02.json')
def main():
    now=int(time.time())
    result={'version':'alpha-0.2-diagnostic','timestamp_utc':datetime.fromtimestamp(now,timezone.utc).isoformat(),
      'repository':os.getenv('GITHUB_REPOSITORY'),'run_id':os.getenv('GITHUB_RUN_ID'),
      'research_only':True,'trading_enabled':False,'signals_enabled':False,
      'release_6_0_0_approved':False,'scores_computed':False,'signals':[],
      'continuous_freshness_proven':False,'source':'OKX Spot','timeframes':{}}
    for tf,(period,bar) in BARS.items():
        data={}; collection={}; relative={}; diagnostic={}
        for asset in ('BTC',)+COINS:
            try:
                parsed=parse_okx_rows(fetch(asset+'-USDT',bar),tf,now)
                data[asset]=parsed
                collection[asset]={'status':'RECEIVED','closed_candles':len(parsed)}
            except Exception as exc:
                collection[asset]={'status':'BLOCKED','error':f'{type(exc).__name__}:{str(exc)[:120]}'}
                data[asset]={}
        for asset in COINS:
            try:
                relative[asset]=relative_close(data[asset],data['BTC'],tf,now)
                diagnostic[asset]=diagnose(data[asset],tf,now,period)
            except Exception as exc:
                relative[asset]={'status':'BLOCKED','reason':f'{type(exc).__name__}:{str(exc)[:120]}'}
                diagnostic[asset]={'status':'BLOCKED','reason':'DIAGNOSTIC_EXCEPTION'}
        result['timeframes'][tf]={'collection':collection,'relative_to_btc':relative,'native_market_diagnostics':diagnostic}
    result['relative_valid_count']=sum(v['status']=='VALIDATED_RELATIVE_CLOSE' for t in result['timeframes'].values() for v in t['relative_to_btc'].values())
    result['diagnostics_valid_count']=sum(v['status']=='RESEARCH_DIAGNOSTICS_ONLY' for t in result['timeframes'].values() for v in t['native_market_diagnostics'].values())
    result['expected_count']=len(COINS)*len(BARS)
    result['outcome']='ALPHA_DIAGNOSTIC_RESEARCH_ONLY'
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Diagnostics:',result['diagnostics_valid_count'],'/',result['expected_count'])
if __name__=='__main__':main()
