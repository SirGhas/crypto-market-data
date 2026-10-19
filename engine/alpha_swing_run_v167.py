"""Fresh 11-asset read-only resistance audit, following existing v1.6.5 pipeline."""
import json
from pathlib import Path
from engine.alpha_swing_run_v165 import main as collect
from engine.alpha_resistance_v167 import closed_candles,overlay

def main():
    collect()
    source=json.loads(Path('artifacts/alpha_swing_v165.json').read_text(encoding='utf-8'))
    histories={}
    for asset in source.get('assets',{}):
        histories[asset]={}
        for tf in ('4h','1D'):
            try:histories[asset][tf]=closed_candles(asset,tf)
            except Exception as e:print('RESISTANCE_CANDLES_UNAVAILABLE',asset,tf,str(e)[:100])
    report=overlay(source,histories)
    path=Path('artifacts/alpha_swing_v167.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V167',json.dumps({'assets':len(report['assets']),
        'audited_assets':report['totals']['resistance_audited_assets'],
        'signals':0,'trades':0}))
if __name__=='__main__':main()
