#!/usr/bin/env python3
"""Collect a SINGLE OKX market history per symbol/tf and reuse it for all research metrics."""
import json,os,time
from datetime import datetime,timezone
from pathlib import Path
from engine.alpha_core import BARS,COINS
from engine.alpha_sma_v04 import collect_history,evaluate

OUT=Path('artifacts/alpha_sma_v04.json')

def main():
    now=int(time.time())
    result={'version':'alpha-0.4-sma-close','timestamp_utc':datetime.fromtimestamp(now,timezone.utc).isoformat(),
            'repository':os.getenv('GITHUB_REPOSITORY'),'run_id':os.getenv('GITHUB_RUN_ID'),
            'research_only':True,'signals_enabled':False,'trading_enabled':False,
            'release_6_0_0_approved':False,'scores_computed':False,'signals':[],
            'continuous_freshness_proven':False,'backtest_completed':False,
            'source':'OKX Spot','timeframes':{},'errors':[]}
    for tf in BARS:
        history={}; collection={}; audit={}
        for asset in ('BTC',)+COINS:
            try:
                history[asset]=collect_history(asset+'-USDT',tf,now)
                collection[asset]={'status':'RECEIVED','closed_candles':len(history[asset])}
            except Exception as exc:
                history[asset]={}
                collection[asset]={'status':'BLOCKED','reason':type(exc).__name__+':'+str(exc)[:130]}
        for asset in COINS:
            try: audit[asset]=evaluate(tf,now,history[asset],history['BTC'])
            except Exception as exc: audit[asset]={'status':'BLOCKED','reason':type(exc).__name__+':'+str(exc)[:130], 'signal_authorized':False}
        result['timeframes'][tf]={'collection':collection,'assets':audit}
    vals=[v for g in result['timeframes'].values() for v in g['assets'].values()]
    result['totals']={'expected':40,'validated':sum(v.get('status')=='RESEARCH_VALIDATED' for v in vals),
                      'blocked':sum(v.get('status')!='RESEARCH_VALIDATED' for v in vals), 'signals':0}
    result['outcome']='RESEARCH_INDICATORS_ONLY'
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Alpha SMA:',result['totals'])
    if result['totals']['blocked']:
        raise SystemExit('Some groups blocked: inspect uploaded artifact')

if __name__=='__main__':main()
