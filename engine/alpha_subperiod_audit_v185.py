"""v1.8.5: descriptive BTC chronological subperiod audit; research only."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_score_audit_v180 import evaluate as replay
from engine.alpha_temporal_audit_v182 import aggregate

def evaluate(bars,lookback=90,horizon=12,stride=12,parts=3):
    if not isinstance(parts,int) or parts<2 or parts>6:raise ValueError('INVALID_PARTS')
    if not isinstance(horizon,int) or not isinstance(stride,int) or horizon<1 or stride<horizon:
        raise ValueError('OVERLAPPING_HORIZONS')
    events=replay(bars,lookback=lookback,horizon=horizon,stride=stride)['events']
    epochs=sorted({e['decision_epoch'] for e in events})
    if len(epochs)<parts*4:raise ValueError('INSUFFICIENT_DECISION_WINDOWS')
    groups=[]
    for k in range(parts):
        start=k*len(epochs)//parts
        end=(k+1)*len(epochs)//parts
        selected=set(epochs[start:end])
        chunk=[e for e in events if e['decision_epoch'] in selected]
        groups.append({'part':k+1,'first_decision_epoch':epochs[start],
                       'last_decision_epoch':epochs[end-1],
                       'counts':aggregate(chunk)})
    return {'version':'alpha-1.8.5-btc-chronological-subperiods',
      'asset':'BTC','timeframe':'4h','horizon_bars':horizon,
      'stride_bars':stride,'subperiods':groups,
      'interpretation':'DESCRIPTIVE_PERIOD_COMPARISON_NOT_REGIME_GENERALIZATION',
      'limitations':['ONE_CONTIGUOUS_HISTORICAL_SLICE','PERIODS_NOT_INDEPENDENT_MARKET_REGIMES',
        'LEVELS_WITHIN_DECISION_CORRELATED','NO_SIGNIFICANCE_TEST',
        'NO_EXECUTION_BACKTEST','NO_CALIBRATED_SCORE_PROBABILITIES'],
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    dest=Path('artifacts/alpha_swing_v185_btc_subperiods.json')
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V185',json.dumps({'periods':[{'part':p['part'],
      'decision_windows':p['counts']['decision_windows'],
      'levels':p['counts']['levels']} for p in report['subperiods']],
      'signals':0,'trades':0}))
if __name__=='__main__':main()
