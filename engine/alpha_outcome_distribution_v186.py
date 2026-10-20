"""v1.8.6 BTC subperiod outcome distribution; descriptive only."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_subperiod_audit_v185 import evaluate as subperiod

def evaluate(bars,parts=3):
    base=subperiod(bars,parts=parts)
    rows=[]
    for p in base['subperiods']:
        bands={}
        for name,c in p['counts']['by_band'].items():
            touched=c['touched']
            outcomes=sum(c[k] for k in ('confirmed_rejections','confirmed_breakouts','ambiguous','unresolved'))
            if outcomes!=touched:raise ValueError('OUTCOME_COUNT_MISMATCH')
            bands[name]={'levels':c['levels'],'touched':touched,
               'confirmed_rejections':c['confirmed_rejections'],
               'confirmed_breakouts':c['confirmed_breakouts'],
               'ambiguous':c['ambiguous'],'unresolved':c['unresolved'],
               'distinct_decisions':c['distinct_decisions'],
               'rejection_share_of_touches_descriptive':round(c['confirmed_rejections']/touched,4) if touched else None}
        rows.append({'part':p['part'],'first_decision_epoch':p['first_decision_epoch'],
          'last_decision_epoch':p['last_decision_epoch'],
          'decision_windows':p['counts']['decision_windows'],'bands':bands})
    return {'version':'alpha-1.8.6-btc-subperiod-outcome-distribution',
      'asset':'BTC','timeframe':'4h','periods':rows,
      'interpretation':'DESCRIPTIVE_SHARES_NOT_PROBABILITIES_OR_SIGNAL_CONFIDENCE',
      'limitations':['SMALL_HIGH_SCORE_SAMPLES','CORRELATED_LEVELS_PER_DECISION',
        'SINGLE_CONTIGUOUS_HISTORY','NO_STATISTICAL_SIGNIFICANCE',
        'NO_INDEPENDENT_REGIME_VALIDATION','NO_EXECUTION_BACKTEST'],
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    path=Path('artifacts/alpha_swing_v186_btc_outcome_distribution.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V186',json.dumps({'periods':[{'part':p['part'],
      'high':p['bands']['HIGH']} for p in report['periods']],
      'signals':0,'trades':0}))
if __name__=='__main__':main()
