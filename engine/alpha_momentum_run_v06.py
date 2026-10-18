"""Single OKX collection reused by SMA233, RSI14, native volume and event study."""
import json, os, time
from datetime import datetime,timezone
from pathlib import Path
from engine.alpha_core import BARS,COINS
from engine.alpha_sma_v04 import collect_history,evaluate
from engine.alpha_momentum_v06 import rsi_wilder,volume_price_action
from engine.alpha_eventstudy_v05 import event_study

def main():
    now=int(time.time())
    report={'version':'alpha-0.6-rsi-volume','timestamp_utc':datetime.fromtimestamp(now,timezone.utc).isoformat(),
            'repository':os.getenv('GITHUB_REPOSITORY'),'run_id':os.getenv('GITHUB_RUN_ID'),
            'research_only':True,'signals_enabled':False,'trading_enabled':False,'release_6_0_0_approved':False,
            'continuous_freshness_proven':False,'backtest_completed':False,'scores_computed':False,'signals':[],
            'source':'OKX Spot','timeframes':{},'totals':{}}
    for tf in BARS:
        rows={}
        for asset in ('BTC',)+COINS:
            try:rows[asset]=collect_history(asset+'-USDT',tf,now)
            except Exception as exc:rows[asset]={}
        block={}
        for asset in COINS:
            try:
                x=evaluate(tf,now,rows[asset],rows['BTC'])
                rsi=rsi_wilder(rows[asset],tf,now)
                volume=volume_price_action(rows[asset],tf,now)
                events=event_study(rows[asset],tf,now)
                identities=[x['sma_close'].get('identity'),rsi.get('identity'),volume.get('identity')]
                valid=(x.get('status')=='RESEARCH_VALIDATED' and
                       rsi.get('status')=='RSI_WILDER_CLOSE_VALIDATED' and
                       volume.get('status')=='NATIVE_VOLUME_PRICE_ACTION_VALIDATED' and
                       events.get('status')=='RESEARCH_EVENT_STUDY_VALID' and len(set(identities))==1)
                block[asset]={'status':'RESEARCH_VALIDATED' if valid else 'BLOCKED',
                              'sma_close':x['sma_close'],'rsi14':rsi,'native_volume_price_action':volume,
                              'event_study':events,'score':None,'tier':None,'validated_trade_rr':None,
                              'signal_authorized':False}
            except Exception as exc:
                block[asset]={'status':'BLOCKED','reason':type(exc).__name__+':'+str(exc)[:150],
                              'signal_authorized':False}
        report['timeframes'][tf]=block
    all_rows=[v for group in report['timeframes'].values() for v in group.values()]
    report['totals']={'expected':40,'validated':sum(x['status']=='RESEARCH_VALIDATED' for x in all_rows),
                      'blocked':sum(x['status']!='RESEARCH_VALIDATED' for x in all_rows),'signals':0}
    report['outcome']='ALPHA_0_6_RESEARCH_ONLY'
    path=Path('artifacts/alpha_momentum_v06.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(report['totals'])
    if report['totals']['blocked']:
        raise SystemExit('Some markets BLOCKED: inspect artifact')
if __name__=='__main__':main()
