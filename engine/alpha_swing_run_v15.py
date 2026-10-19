"""Collect v1.4 with unchanged v1.2/1.3/1.4 chain, then add v1.5 overlay."""
import json
from pathlib import Path
from engine.alpha_swing_run_v14 import main as collect_v14
from engine.alpha_risk_v15 import overlay

def main():
    collect_v14()
    p=Path('artifacts/alpha_swing_v14.json')
    result=overlay(json.loads(p.read_text(encoding='utf-8')))
    target=Path('artifacts/alpha_swing_v15.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V15',json.dumps({'atr_validated':result['totals']['atr_both_timeframes_validated'],
                                 'signals':len(result['signals']),'trading_enabled':result['trading_enabled']}))

if __name__=='__main__':main()
