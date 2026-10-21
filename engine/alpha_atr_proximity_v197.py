"""v1.9.7: volatility-normalized proximity for mixed BTC level outcomes."""
import json
from collections import defaultdict
from decimal import Decimal,InvalidOperation
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_level_proximity_v196 import proximity

R='CONFIRMED_REJECTION';B='CONFIRMED_CLOSE_THROUGH'
THRESHOLDS=(Decimal('0.25'),Decimal('0.5'),Decimal('1'))
def atr_at_decision(bars,lookback=14):
    result={}
    for i in range(lookback,len(bars)):
        window=bars[i-lookback:i]
        tr=[]
        for j,b in enumerate(window):
            prev=bars[i-lookback+j-1][4] if i-lookback+j>0 else b[4]
            tr.append(max(b[2]-b[3],abs(b[2]-prev),abs(b[3]-prev)))
        atr=sum(tr,Decimal(0))/Decimal(lookback)
        if atr<=0:raise ValueError('NON_POSITIVE_ATR')
        result[bars[i][0]]=atr
    return result

def analyze(bars,events):
    atrs=atr_at_decision(bars)
    groups=defaultdict(list)
    for e in events:
        if e['outcome'] not in (R,B):continue
        epoch=e['decision_epoch']
        if not isinstance(epoch,int) or isinstance(epoch,bool):raise ValueError('INVALID_EPOCH')
        try:p=Decimal(str(e['level']))
        except (InvalidOperation,ValueError,TypeError):raise ValueError('INVALID_LEVEL')
        if not p.is_finite() or p<=0:raise ValueError('INVALID_LEVEL')
        groups[epoch].append((p,e['outcome']))
    counts={'mixed_windows':0}
    for threshold in THRESHOLDS:counts['within_'+str(threshold)+'_atr']=0
    details=[]
    for epoch,rows in sorted(groups.items()):
        rejects={p for p,o in rows if o==R}
        breaks={p for p,o in rows if o==B}
        if not rejects or not breaks:continue
        if epoch not in atrs:raise ValueError('MISSING_CAUSAL_ATR')
        dist=min(abs(a-b) for a in rejects for b in breaks)/atrs[epoch]
        counts['mixed_windows']+=1
        for threshold in THRESHOLDS:
            if dist<=threshold:counts['within_'+str(threshold)+'_atr']+=1
        details.append({'decision_epoch':epoch,'nearest_pair_distance_atr':str(dist.normalize())})
    return {'counts':counts,'details':details}

def evaluate(bars):
    quality=audit(bars)
    events=replay(bars)['events']
    result=analyze(bars,events)
    reference=proximity(events)
    if result['counts']['mixed_windows']!=reference['counts']['mixed_windows']:
        raise ValueError('MIXED_WINDOW_COUNT_MISMATCH')
    return {'version':'alpha-1.9.7-btc-atr-normalized-level-proximity',
      'asset':'BTC','timeframe':'4h','history_quality':quality,**result,
      'atr_method':'PRE_DECISION_14_BAR_SIMPLE_TRUE_RANGE_MEAN',
      'interpretation':'DESCRIPTIVE_ATR_DISTANCE_NOT_SAME_ZONE_PROOF',
      'limitations':['ATR_LOOKBACK_FIXED_AT_14','NO_ATR_THRESHOLD_CALIBRATION',
        'MULTIPLE_LEVELS_PER_WINDOW','NO_INDEPENDENT_REGIME_VALIDATION',
        'NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v197_btc_atr_level_proximity.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V197',json.dumps({'counts':report['counts'],
      'atr_method':report['atr_method'],'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
