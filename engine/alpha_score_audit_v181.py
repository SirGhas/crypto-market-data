"""v1.8.1 BTC 4h structural-score coverage audit (research-only).
Reuses causal historical observations from v1.8.0. All bins are descriptive.
"""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_score_audit_v180 import evaluate as baseline
from engine.alpha_importance_v179 import score_level

BINS=(('LOW',0,48),('MEDIUM',48,54),('HIGH',54,101))

def coverage(bars,lookback=90,horizon=12,stride=12):
    base=baseline(bars,lookback=lookback,horizon=horizon,stride=stride)
    events=base['events']
    # Boundaries selected for reachability under current 4h formula, NOT tuned
    # to improve outcomes. Keep exact score counts for later scrutiny.
    groups={}
    for name,lower,upper in BINS:
        rows=[e for e in events if lower<=e['heuristic_score']<upper]
        hits=[e for e in rows if e['outcome']!='NO_TOUCH']
        groups[name]={'observations':len(rows),'touched':len(hits),
          'confirmed_rejections':sum(e['outcome']=='CONFIRMED_REJECTION' for e in hits),
          'confirmed_breakouts':sum(e['outcome']=='CONFIRMED_CLOSE_THROUGH' for e in hits),
          'ambiguous':sum(e['outcome']=='TOUCH_AMBIGUOUS' for e in hits),
          'unresolved':sum(e['outcome']=='TOUCH_UNRESOLVED' for e in hits)}
    scores=sorted(set(e['heuristic_score'] for e in events))
    assert sum(x['observations'] for x in groups.values())==len(events)
    return {'version':'alpha-1.8.1-btc-4h-score-coverage',
      'asset':'BTC','timeframe':'4h','closed_bars':len(bars),
      'bin_thresholds':{name:{'min_inclusive':lo,'max_exclusive':hi} for name,lo,hi in BINS},
      'theoretical_max_4h_score':score_level('4h',999,999),
      'observed_min_score':min(scores) if scores else None,
      'observed_max_score':max(scores) if scores else None,
      'distinct_scores':scores,'groups':groups,
      'note':'Bin boundaries set to avoid unreachable group; not predictive calibration',
      'limitations':['4H_ONLY','GROUP_THRESHOLDS_NOT_OPTIMIZED',
        'MULTIPLE_LEVELS_FROM_SAME_WINDOW_NOT_INDEPENDENT',
        'NO_OUT_OF_SAMPLE_VALIDATION','NO_TRADING_OR_EXECUTION_BACKTEST'],
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}

def main():
    report=coverage(history_4h(pages=12))
    path=Path('artifacts/alpha_swing_v181_btc_score_coverage.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V181',json.dumps({'max':report['theoretical_max_4h_score'],
        'groups':report['groups'],'trades':0,'signals':0}))
if __name__=='__main__':main()
