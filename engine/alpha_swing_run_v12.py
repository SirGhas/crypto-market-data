"""GitHub manual research run. Fail closed when any data stream is absent."""
import argparse,json,os,time
from datetime import datetime,timezone
from pathlib import Path
from engine.alpha_core import BARS,COINS
from engine.alpha_sma_v04 import collect_history
from engine.alpha_swing_v11 import inspect
from engine.alpha_swing_v12 import TFS,snapshot

def main():
    a=argparse.ArgumentParser();a.add_argument('--previous');args=a.parse_args()
    BARS.update({'30m':(1800,'30m'),'2h':(7200,'2H'),'1D':(86400,'1Dutc')})
    now=int(time.time());markets={};failures=[]
    for tf in TFS:
        markets[tf]={}
        for asset in COINS:
            try:markets[tf][asset]=inspect(collect_history(asset+'-USDT',tf,now),tf,now)
            except Exception as e:markets[tf][asset]={'status':'BLOCKED','reason':type(e).__name__+':'+str(e)[:130]}
            if markets[tf][asset]['status']!='VALIDATED':failures.append(tf+':'+asset)
            time.sleep(.12)
    previous=json.loads(Path(args.previous).read_text(encoding='utf8')) if args.previous and Path(args.previous).exists() else None
    report=snapshot(markets,now,previous)
    report.update({'utc_time':datetime.fromtimestamp(now,timezone.utc).isoformat(),'github_run_id':os.environ.get('GITHUB_RUN_ID'),'baseline_available':previous is not None,'collection_errors':failures})
    out=Path('artifacts/alpha_swing_v12.json');out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report['totals'],ensure_ascii=False))
    if failures or report['cross_run']['anomalies']:raise SystemExit('FAIL_CLOSED: collection/freshness errors; see output artifact')
if __name__=='__main__':main()
