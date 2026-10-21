"""v1.9.0 closed BTC 4h history provenance and integrity research audit."""
import hashlib,json
from decimal import Decimal,InvalidOperation
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_high_evidence_tiers_v189 import evaluate as tiers

def audit(bars):
    if not bars:raise ValueError('EMPTY_HISTORY')
    last=None; normalized=[]
    for b in bars:
        if len(b)!=6:raise ValueError('BAD_BAR_SHAPE')
        t=b[0]
        if not isinstance(t,int) or isinstance(t,bool) or t%14400:raise ValueError('INVALID_TIMESTAMP')
        if last is not None and t-last!=14400:raise ValueError('NON_CONTIGUOUS_HISTORY')
        last=t
        try:o,h,l,c,v=(Decimal(str(x)) for x in b[1:])
        except (InvalidOperation,ValueError):raise ValueError('NON_NUMERIC_BAR')
        if not all(x.is_finite() for x in (o,h,l,c,v)):raise ValueError('NON_FINITE_BAR')
        if min(o,h,l,c)<=0 or v<0 or h<max(o,c,l) or l>min(o,c,h):
            raise ValueError('INVALID_OHLCV')
        normalized.append([t]+[str(x) for x in (o,h,l,c,v)])
    fingerprint=hashlib.sha256(json.dumps(normalized,separators=(',',':')).encode()).hexdigest()
    return {'bar_count':len(bars),'first_closed_epoch':bars[0][0],
      'last_closed_epoch':bars[-1][0],'expected_interval_seconds':14400,
      'contiguous':True,'ohlcv_valid':True,'sha256_normalized_history':fingerprint}

def evaluate(bars):
    quality=audit(bars)
    evidence=tiers(bars)
    return {'version':'alpha-1.9.0-btc-history-quality','asset':'BTC','timeframe':'4h',
      'source':'OKX BTC-USDT 4H history-candles','history_quality':quality,
      'evidence_tiers':evidence['periods'],
      'interpretation':'DATA_INTEGRITY_CHECK_NOT_INDEPENDENT_SOURCE_VERIFICATION',
      'limitations':['SINGLE_DATA_PROVIDER','NO_CROSS_PROVIDER_RECONCILIATION',
        'NO_LONG_TERM_ARCHIVE_ATTESTATION','NO_STATISTICAL_VALIDATION',
        'NO_EXECUTION_BACKTEST'],
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v190_btc_history_quality.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V190',json.dumps({'history_quality':report['history_quality'],
      'periods':report['evidence_tiers'],'signals':0,'trades':0}))
if __name__=='__main__':main()
