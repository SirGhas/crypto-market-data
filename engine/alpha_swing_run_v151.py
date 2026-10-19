"""Run unchanged v1.5 pipeline, then attach resistance research gates."""
import json
from pathlib import Path
from engine.alpha_swing_run_v15 import main as collect_v15
from engine.alpha_resistance_v151 import overlay

def main():
    collect_v15()
    source=Path('artifacts/alpha_swing_v15.json')
    report=overlay(json.loads(source.read_text(encoding='utf-8')))
    path=Path('artifacts/alpha_swing_v151.json')
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V151',json.dumps({'assets':report['totals']['resistance_gates'],'trades':0,'signals':0}))

if __name__=='__main__':main()
