"""v2.0.1: denominated mixed-window frequencies by equal-duration period."""
import json
from decimal import Decimal
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_equal_duration_v200 import evaluate as base_evaluate

def rates(periods):
    output=[]
    totals={'candidate_decision_windows':0,'mixed_windows':0,'within_1_atr':0}
    for period in periods:
        denominator=period['candidate_decision_windows']
        mixed=period['mixed_windows']
        near=period['within_threshold_counts']['1']
        if any(not isinstance(v,int) or isinstance(v,bool) for v in (denominator,mixed,near)):
            raise ValueError('INVALID_COUNT')
        if denominator<=0 or mixed<0 or mixed>denominator or near<0 or near>mixed:
            raise ValueError('INVALID_DENOMINATOR_OR_COUNT')
        totals['candidate_decision_windows']+=denominator
        totals['mixed_windows']+=mixed
        totals['within_1_atr']+=near
        output.append({'part':period['part'],'candidate_decision_windows':denominator,
          'mixed_windows':mixed,'mixed_share_of_candidate_windows_pct':
              str((Decimal(100)*mixed/denominator).quantize(Decimal('0.01'))),
          'mixed_within_1_atr':near,
          'within_1_atr_share_of_mixed_pct':str((Decimal(100)*near/mixed).quantize(Decimal('0.01'))) if mixed else None,
          'within_1_atr_share_of_all_candidate_windows_pct':
              str((Decimal(100)*near/denominator).quantize(Decimal('0.01')))})
    return {'period_rates':output,'totals':totals,
      'overall_mixed_share_pct':str((Decimal(100)*totals['mixed_windows']/
         totals['candidate_decision_windows']).quantize(Decimal('0.01'))) if totals['candidate_decision_windows'] else None}
def evaluate(bars):
    base=base_evaluate(bars)
    result=rates(base['equal_duration_periods'])
    if result['totals']['mixed_windows']!=base['mixed_windows']:
        raise ValueError('MIXED_RECONCILIATION_FAILED')
    return {'version':'alpha-2.0.1-btc-denominated-mixed-window-frequencies',
      'asset':'BTC','timeframe':'4h','history_quality':base['history_quality'],
      **result,'denominator':'ALL_CANDIDATE_DECISION_WINDOWS_PER_EQUAL_DURATION_PERIOD',
      'interpretation':'DESCRIPTIVE_WINDOW_FREQUENCY_NOT_PROBABILITY_OF_TRADE_SUCCESS',
      'limitations':['WINDOWS_NOT_INDEPENDENT','NO_CONFIDENCE_INTERVALS',
        'SMALL_SUBPERIOD_COUNTS','NO_EXECUTION_BACKTEST'],
      'signal_generation':{'status':'DISABLED_BY_SAFETY_POLICY','generated_signals':None},
      'research_only':True,'signals':[],'signals_enabled':False,
      'trading_enabled':False,'trade_authorized':False,
      'backtest_completed':False,'continuous_freshness_proven':False,
      'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    p=Path('artifacts/alpha_swing_v201_btc_denominated_frequencies.json')
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V201',json.dumps({'period_rates':report['period_rates'],
      'totals':report['totals'],'signal_generation':report['signal_generation']}))
if __name__=='__main__':main()
