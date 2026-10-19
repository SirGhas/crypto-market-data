"""Run preserved Alpha 1.6.3 chain and append read-only market-buy scenarios."""
import json
from pathlib import Path
from engine.alpha_swing_run_v163 import main as collect_v163
from engine.alpha_market_buy_v164 import overlay

def main():
    collect_v163()
    report=json.loads(Path('artifacts/alpha_swing_v163.json').read_text(encoding='utf-8'))
    final=overlay(report)
    out=Path('artifacts/alpha_swing_v164.json')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V164',json.dumps({
       'assets':final['totals']['market_buy_assets'],
       'scenarios_computed':final['totals']['market_buy_scenarios_computed'],
       'execution_validated':0,'trading_enabled':False,'signals':0}))
if __name__=='__main__':main()
