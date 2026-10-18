"""Execute existing v1.3 research collection, then attach v1.4 conservative risk overlay."""
import json
from pathlib import Path
from engine.alpha_swing_run_v13 import main as collect_v13
from engine.alpha_risk_v14 import overlay

def main():
    collect_v13()
    source=Path('artifacts/alpha_swing_v13.json')
    result=overlay(json.loads(source.read_text(encoding='utf-8')))
    output=Path('artifacts/alpha_swing_v14.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V14',json.dumps({'risk_records':len(result['risk_research']),
                                  'bundled_alerts':len(result['alert_bundles']),
                                  'trading_enabled':result['trading_enabled']}))
if __name__=='__main__':main()
