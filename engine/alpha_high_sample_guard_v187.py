"""v1.8.7 descriptive HIGH-score sample sufficiency guard; never a signal."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_outcome_distribution_v186 import evaluate as distribution

MIN_TOUCHES=20
def evaluate(bars,minimum_touches=MIN_TOUCHES):
    if not isinstance(minimum_touches,int) or isinstance(minimum_touches,bool) or minimum_touches<1:
        raise ValueError('INVALID_MINIMUM_TOUCHES')
    source=distribution(bars)
    periods=[]
    for p in source['periods']:
        high=p['bands']['HIGH']
        touches=high['touched']
        periods.append({'part':p['part'],'high_touches':touches,
          'high_distinct_decisions':high['distinct_decisions'],
          'confirmed_rejections':high['confirmed_rejections'],
          'confirmed_breakouts':high['confirmed_breakouts'],
          'sample_sufficiency':'INSUFFICIENT' if touches<minimum_touches else 'COUNT_THRESHOLD_MET_NOT_VALIDATED'})
    return {'version':'alpha-1.8.7-btc-high-sample-guard',
      'asset':'BTC','timeframe':'4h','minimum_touches_descriptive':minimum_touches,
      'periods':periods,'all_periods_meet_count_threshold':all(
        p['high_touches']>=minimum_touches for p in periods),
      'interpretation':'COUNT_GUARD_ONLY_NO_STATISTICAL_CONFIDENCE_OR_TRADING_ELIGIBILITY',
      'limitations':['ARBITRARY_PREDECLARED_COUNT_THRESHOLD','CORRELATED_LEVELS',
        'SINGLE_HISTORICAL_SLICE','NO_INDEPENDENT_REGIME_VALIDATION',
        'NO_EXECUTION_BACKTEST','NOT_A_PROBABILITY_ESTIMATE'],
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    result=evaluate(history_4h(pages=12))
    path=Path('artifacts/alpha_swing_v187_btc_high_sample_guard.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V187',json.dumps({'periods':result['periods'],
      'all_periods_meet_count_threshold':result['all_periods_meet_count_threshold'],
      'signals':0,'trades':0}))
if __name__=='__main__':main()
