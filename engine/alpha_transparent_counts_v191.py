"""v1.9.1: separate research observations from deliberately disabled signals."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_history_quality_v190 import audit
from engine.alpha_outcome_distribution_v186 import evaluate as distribution
from engine.alpha_high_evidence_tiers_v189 import tier

def evaluate(bars):
    quality=audit(bars)
    source=distribution(bars)
    periods=[]
    totals={k:0 for k in ('identified_level_observations','historical_confirmed_rejections',
      'historical_confirmed_breakouts','historical_ambiguous','historical_unresolved',
      'historical_no_touch','historical_touches')}
    for p in source['periods']:
        bands=p['bands']
        counts={k:0 for k in totals}
        for b in ('LOW','MEDIUM','HIGH'):
            c=bands[b]
            n=c['levels']; touched=c['touched']
            if not isinstance(n,int) or not isinstance(touched,int) or n<0 or not 0<=touched<=n:
                raise ValueError('INVALID_RESEARCH_COUNTS')
            if sum(c[k] for k in ('confirmed_rejections','confirmed_breakouts','ambiguous','unresolved'))!=touched:
                raise ValueError('INCONSISTENT_RESEARCH_OUTCOMES')
            counts['identified_level_observations']+=n
            counts['historical_touches']+=touched
            counts['historical_no_touch']+=n-touched
            for dest,key in (('historical_confirmed_rejections','confirmed_rejections'),
                             ('historical_confirmed_breakouts','confirmed_breakouts'),
                             ('historical_ambiguous','ambiguous'),
                             ('historical_unresolved','unresolved')):
                counts[dest]+=c[key]
        for key in totals:totals[key]+=counts[key]
        periods.append({'part':p['part'],**counts,
          'high_touches':bands['HIGH']['touched'],
          'high_evidence_tier':tier(bands['HIGH']['touched'])})
    return {'version':'alpha-1.9.1-btc-transparent-research-counts',
      'asset':'BTC','timeframe':'4h','history_quality':quality,
      'counting_unit':'LEVEL_OBSERVATION_PER_DECISION_WINDOW_NOT_UNIQUE_PRICE_LEVEL',
      'historical_reaction_definition':'CONFIRMED_REJECTION_PROXY_NOT_TRADING_SIGNAL',
      'totals':totals,'periods':periods,
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY',
         'generated_signals':None,'zero_does_not_mean_no_market_opportunities':True},
      'interpretation':'HISTORICAL_DESCRIPTIVE_COUNTS_ONLY',
      'limitations':['SAME_LEVEL_MAY_RECUR_ACROSS_WINDOWS',
        'LEVEL_OBSERVATIONS_NOT_INDEPENDENT','SINGLE_HISTORICAL_SLICE',
        'NO_PREDICTIVE_CALIBRATION','NO_EXECUTION_BACKTEST'],
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v191_btc_transparent_counts.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V191',json.dumps({'totals':report['totals'],
       'periods':report['periods'],'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
