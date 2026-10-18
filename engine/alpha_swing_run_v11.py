"""Manual, fail-closed OKX multi-timeframe research watch runner."""
import argparse,json,time,os
from datetime import datetime,timezone
from pathlib import Path
from engine.alpha_core import BARS,COINS
from engine.alpha_sma_v04 import collect_history
from engine.alpha_swing_v11 import inspect,build_report

def main():
    p=argparse.ArgumentParser();p.add_argument('--previous',default=None);args=p.parse_args()
    # Keep legacy algorithms unchanged; extend their shared dictionary at runtime.
    BARS.update({'2h':(7200,'2H'),'1D':(86400,'1Dutc')})
    now=int(time.time());markets={};failures=[]
    for tf in ('1h','2h','4h','1D'):
        group={}
        for asset in COINS:
            try:group[asset]=inspect(collect_history(asset+'-USDT',tf,now),tf,now)
            except Exception as exc:
                group[asset]={'status':'BLOCKED','reason':type(exc).__name__+':'+str(exc)[:100]}
            if group[asset]['status']!='VALIDATED':failures.append(f'{tf}:{asset}:{group[asset].get("reason")}')
            time.sleep(.10)
        markets[tf]=group
    prev=None
    if args.previous:
        try:
            prev=json.loads(Path(args.previous).read_text(encoding='utf8'))
            if prev.get('version')!='alpha-1.1-swing-watch':raise ValueError('OLD_VERSION')
        except (OSError,ValueError) as exc:raise SystemExit(f'Previous baseline invalid: {exc}')
    report=build_report(markets,now,prev)
    report['utc_time']=datetime.fromtimestamp(now,timezone.utc).isoformat()
    report['github_run_id']=os.getenv('GITHUB_RUN_ID')
    report['collection_errors']=failures
    report['baseline_available']=bool(prev)
    out=Path('artifacts/alpha_swing_v11.json');out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report['totals']))
    if failures:raise SystemExit(f'{len(failures)} blocked markets; review artifact')
if __name__=='__main__':main()
