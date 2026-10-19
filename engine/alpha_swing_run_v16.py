"""Run unchanged v1.5.1 pipeline, then append partial pivot-zone research overlay."""
import json
from pathlib import Path
from engine.alpha_swing_run_v151 import main as collect_v151
from engine.alpha_levels_v16 import overlay

def main():
    collect_v151()
    path=Path('artifacts/alpha_swing_v151.json')
    report=overlay(json.loads(path.read_text(encoding='utf-8')))
    target=Path('artifacts/alpha_swing_v16.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V16',json.dumps({'assets':report['totals']['level_quality_assets'],
         'partial':report['totals']['level_quality_partial'],'signals':0}))

if __name__=='__main__':main()
