"""v1.8.8 HIGH evidence-gap audit: sample counts and decision clusters only."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_high_sample_guard_v187 import evaluate as guard

def evaluate(bars,minimum_touches=20):
    base=guard(bars,minimum_touches=minimum_touches)
    rows=[]
    for p in base['periods']:
        touched=p['high_touches']
        decisions=p['high_distinct_decisions']
        if touched<0 or decisions<0:raise ValueError('NEGATIVE_COUNTS')
        rows.append({'part':p['part'],'observed_high_touches':touched,
          'high_decision_windows':decisions,
          'touch_shortfall_to_descriptive_threshold':max(0,minimum_touches-touched),
          'threshold_met':touched>=minimum_touches,
          'interpretation':'DESCRIPTIVE_SAMPLE_COUNT_NOT_INDEPENDENT_EVIDENCE'})
    return {'version':'alpha-1.8.8-btc-high-evidence-gap',
      'asset':'BTC','timeframe':'4h','minimum_touches_descriptive':minimum_touches,
      'periods':rows,'all_periods_meet_count_threshold':all(p['threshold_met'] for p in rows),
      'additional_data_needed':'INDEPENDENT_HISTORICAL_REGIMES_AND_MORE_DECISION_EPISODES',
      'limitations':['NO_EXTRAPOLATION_OF_COLLECTION_TIME',
         'LEVELS_CORRELATED_WITHIN_WINDOWS','ONE_MARKET_SLICE',
         'COUNT_THRESHOLD_NOT_STATISTICAL_POWER','NO_TRADE_BACKTEST'],
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v188_btc_high_evidence_gap.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V188',json.dumps({'periods':report['periods'],
       'signals':0,'trades':0}))
if __name__=='__main__':main()
