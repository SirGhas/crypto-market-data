"""Full data collection via v1.2, directional classification via v1.3."""
import json,sys
from pathlib import Path
from engine.alpha_swing_run_v12 import main as collect_v12
from engine.alpha_alerts_v13 import classify

def main():
    old13=Path('artifacts/previous_alpha_swing_v13.json')
    old12=Path('artifacts/previous_alpha_swing_v12.json')
    prev=json.loads(old13.read_text()) if old13.exists() else (json.loads(old12.read_text()) if old12.exists() else None)
    # v1.2 snapshot accepts only a v1.2 previous version; use adapted copy, not mutation.
    compatible=Path('artifacts/previous_alpha_for_v12.json')
    if prev is not None:
        adapted=dict(prev, version='alpha-1.2-multi-timeframe-watch')
        compatible.parent.mkdir(parents=True, exist_ok=True)
        compatible.write_text(json.dumps(adapted))
    argv=sys.argv
    try:
        sys.argv=[argv[0]]+(['--previous',str(compatible)] if prev is not None else [])
        collect_v12()
    finally:sys.argv=argv
    current=json.loads(Path('artifacts/alpha_swing_v12.json').read_text())
    result=classify(prev,current)
    out=Path('artifacts/alpha_swing_v13.json')
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V13',json.dumps({'status':result['alert_status'],'alerts':len(result['research_alerts'])}))
if __name__=='__main__':main()
