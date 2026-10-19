"""Manual BTC-only body-first, wick-aware six-timeframe probe."""
import json
from pathlib import Path
from engine.alpha_body_levels_v168 import btc_probe

def main():
    data=btc_probe()
    path=Path('artifacts/alpha_swing_v168_btc.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V168',json.dumps({'asset':'BTC','timeframes':len(data['timeframes']),
        '4h_support':(data['primary_support'] or {}).get('body_level'),
        '4h_resistance':(data['primary_resistance'] or {}).get('body_level'),
        'signals':0,'trading_enabled':False}))
if __name__=='__main__':main()
