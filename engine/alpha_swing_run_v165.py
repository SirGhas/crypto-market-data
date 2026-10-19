"""Isolated v1.6.5 market-buy depth experiment. No order endpoints."""
import json
import time
from pathlib import Path
from engine.alpha_swing_run_v164 import main as collect_v164
from engine.alpha_swing_run_v162 import UNIVERSE
from engine.alpha_depth_v165 import fetch_book,overlay

def main():
    collect_v164()
    base=json.loads(Path('artifacts/alpha_swing_v164.json').read_text(encoding='utf-8'))
    books={}
    for asset in UNIVERSE:
        try:
            books[asset]=fetch_book(asset)
        except Exception as exc:
            books[asset]={'status':'UNAVAILABLE','reason':type(exc).__name__+':'+str(exc)[:120]}
        time.sleep(0.15)
    final=overlay(base,books)
    output=Path('artifacts/alpha_swing_v165.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V165',json.dumps({
        'assets':len(UNIVERSE),
        'observed_depth_books':sum(x.get('status')=='OBSERVED' for x in books.values()),
        'depth_scenarios_computed':final['totals']['depth_scenarios_computed'],
        'trades':0,'signals':0}))

if __name__=='__main__':main()
