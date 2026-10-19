"""Single manual experimental read-only run: v16 plus OHLCV and 3 live book samples."""
import json,time
from pathlib import Path
from engine.alpha_swing_run_v16 import main as collect_v16
from engine.alpha_evidence_v161 import closed_volume_candles,book_sample,check_book_series,evidence_overlay

def main():
    collect_v16()
    base=json.loads(Path('artifacts/alpha_swing_v16.json').read_text(encoding='utf8'))
    histories={}; samples={}; books={};errors={}
    assets=sorted(base.get('assets',{}))
    for asset in assets:
        m=base['assets'][asset]
        try:
            histories[asset]={}
            for tf,bar in [('4h','4H'),('1D','1Dutc')]:
                ref=m['timeframes'][tf]
                ts=int(ref['identity'].split(':')[0]); close=ref['close']
                histories[asset][tf]=closed_volume_candles(asset,bar,ts,close)
        except Exception as e:
            histories.pop(asset,None);errors.setdefault(asset,[]).append('OHLCV_'+type(e).__name__+':'+str(e)[:100])
    # Three *real*, time-separated exchange book snapshots, no invented history.
    for sample_no in range(3):
        if sample_no:time.sleep(3)
        for asset in assets:
            try:samples.setdefault(asset,[]).append(book_sample(asset))
            except Exception as e:errors.setdefault(asset,[]).append('BOOK_'+type(e).__name__+':'+str(e)[:100])
    for asset in assets:
        try:
            summary=check_book_series(samples.get(asset,[]))
            books[asset]={'status':'OBSERVED','summary':summary,'snapshots':samples[asset]}
        except Exception as e:
            books[asset]={'status':'NOT_VALIDATED','reason':str(e)[:100],'snapshots':samples.get(asset,[])}
    result=evidence_overlay(base,histories,books)
    result['evidence_collection_errors']=errors
    result['experiment_scope']='ONE_MANUAL_RUN_THREE_SEPARATED_LIVE_BOOK_SNAPSHOTS'
    path=Path('artifacts/alpha_swing_v161.json');path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('ALPHA_V161',json.dumps({'assets':len(assets),'ohclv_validated':len(histories),
        'books_observed':sum(b['status']=='OBSERVED' for b in books.values()),
        'errors':sum(map(len,errors.values())),'signals':0}))

if __name__=='__main__':main()
