"""v1.8.3 BTC score sensitivity audit on non-overlapping decision windows.
Research only; outcome counts are descriptive, not probabilities.
"""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_temporal_audit_v182 import aggregate

def evaluate(bars,lookback=90,horizon=12,stride=12):
    if stride<horizon:raise ValueError('OVERLAPPING_FUTURE_HORIZONS')
    if stride<=0 or horizon<=0:raise ValueError('INVALID_WINDOW')
    baseline=replay(bars,lookback=lookback,horizon=horizon,stride=stride)
    events=baseline['events']
    decisions=sorted({e['decision_epoch'] for e in events})
    if len(decisions)<8:raise ValueError('INSUFFICIENT_DECISIONS')
    cut=len(decisions)*3//5
    split=decisions[cut]
    first=[e for e in events if e['decision_epoch']<split]
    second=[e for e in events if e['decision_epoch']>=split]
    if not first or not second:raise ValueError('EMPTY_SPLIT')
    # Multiple levels within one decision share a price path: no independent trial claim.
    return {'version':'alpha-1.8.3-btc-4h-nonoverlap-audit',
        'asset':'BTC','timeframe':'4h','horizon_bars':horizon,
        'stride_bars':stride,'decision_windows_total':len(decisions),
        'train':aggregate(first),'held_out':aggregate(second),
        'independence':'NONOVERLAPPING_FUTURE_WINDOWS_ONLY; LEVELS_WITHIN_WINDOW_DEPENDENT',
        'limitations':['SINGLE_BTC_HISTORICAL_SLICE','SAME_PRICE_REGIMES_POSSIBLE',
          'LEVELS_WITHIN_DECISION_NOT_INDEPENDENT','NO_SIGNIFICANCE_INFERENCE',
          'NO_MULTI_TIMEFRAME_VALIDATION','NOT_A_PREDICTIVE_PROBABILITY',
          'NO_EXECUTION_BACKTEST'],
        'research_only':True,'signals':[],'signals_enabled':False,
        'trading_enabled':False,'trade_authorized':False,
        'backtest_completed':False,'continuous_freshness_proven':False,
        'release_6_0_0_approved':False}

def main():
    data=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v183_btc_nonoverlap.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V183',json.dumps({'train':data['train'],'held_out':data['held_out'],
                                  'signals':0,'trades':0}))
if __name__=='__main__':main()
