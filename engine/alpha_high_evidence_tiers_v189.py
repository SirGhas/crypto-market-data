"""v1.8.9: predeclared descriptive HIGH-touch evidence tiers, never validation."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_high_sample_guard_v187 import evaluate as guard

def tier(n):
    if not isinstance(n,int) or isinstance(n,bool) or n<0:raise ValueError('INVALID_TOUCH_COUNT')
    if n<5:return 'VERY_LIMITED'
    if n<10:return 'PRELIMINARY_REVIEW'
    return 'DESCRIPTIVE_COMPARISON_ONLY'

def evaluate(bars):
    # Existing v1.8.7 guard is a source of counts, not the v1.8.9 threshold.
    base=guard(bars)
    rows=[]
    for p in base['periods']:
        n=p['high_touches']
        rows.append({'part':p['part'],'high_touches':n,
          'high_distinct_decisions':p['high_distinct_decisions'],
          'evidence_tier':tier(n),'preliminary_review_allowed':n>=5,
          'descriptive_comparison_allowed':n>=10})
    return {'version':'alpha-1.8.9-btc-high-evidence-tiers',
      'asset':'BTC','timeframe':'4h','tier_boundaries':{'very_limited_below':5,
        'preliminary_review_from':5,'descriptive_comparison_from':10},
      'periods':rows,'interpretation':'DESCRIPTIVE_TIERS_NOT_STATISTICAL_VALIDATION',
      'limitations':['TOUCHES_NOT_INDEPENDENT_OBSERVATIONS',
        'THRESHOLDS_ARE_HEURISTIC_NOT_POWER_ANALYSIS','SINGLE_HISTORICAL_SLICE',
        'NO_INDEPENDENT_REGIME_VALIDATION','NO_TRADING_ELIGIBILITY'],
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v189_btc_high_evidence_tiers.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V189',json.dumps({'periods':report['periods'],'signals':0,'trades':0}))
if __name__=='__main__':main()
