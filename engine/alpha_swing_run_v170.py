"""Manual BTC multi-window structural robustness check."""
import json,time,urllib.request,urllib.parse
from pathlib import Path
from engine.alpha_body_levels_v168 import TIMEFRAMES,parse,extract
from engine.alpha_stability_v170 import audit

def main():
    now=int(time.time())
    histories={}
    for tf,(bar,period) in TIMEFRAMES.items():
        url='https://www.okx.com/api/v5/market/candles?'+urllib.parse.urlencode(
            {'instId':'BTC-USDT','bar':bar,'limit':'100'})
        req=urllib.request.Request(url,headers={'User-Agent':'alpha-stability-v170/1.0'})
        with urllib.request.urlopen(req,timeout=18) as f:response=json.load(f)
        if response.get('code')!='0':raise ValueError('OKX_UNAVAILABLE_'+tf)
        histories[tf]=parse(response['data'],tf,now)
    base={'version':'alpha-1.6.8-btc-body-wick-probe','asset':'BTC',
          'timeframes':{tf:extract(tf,rows) for tf,rows in histories.items()}}
    output=audit(base,histories['4h'],histories['1D'])
    path=Path('artifacts/alpha_swing_v170_btc.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V170',json.dumps({'primary_reference_level':output['primary_reference_level'],
      'stability_status':output['stability_status'],
      'matching_windows':output['windows_matching_primary_area'],
      'windows_tested':output['windows_tested'],'trade_authorized':False}))
if __name__=='__main__':main()
