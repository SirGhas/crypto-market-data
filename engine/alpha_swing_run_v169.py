"""BTC research-only structural rank, based on fresh 1.6.8 six-timeframe audit."""
import json
from pathlib import Path
from engine.alpha_body_levels_v168 import btc_probe
from engine.alpha_structure_v169 import rank_primary

def main():
    base=btc_probe()
    output=rank_primary(base)
    path=Path('artifacts/alpha_swing_v169_btc.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('ALPHA_V169',json.dumps({'primary_candidate':(output['primary_candidate_4h'] or {}).get('body_level'),
      'nearest_4h_resistance':output['nearest_4h_resistance'],
      'zones':len(output['ranked_resistances_4h']),'trades':0,'signals':0}))
if __name__=='__main__':main()
