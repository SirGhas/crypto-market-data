"""v1.8.4 research-only sensitivity audit: vary horizons without tuning bins."""
import json
from pathlib import Path
from engine.alpha_walkforward_v171 import history_4h
from engine.alpha_nonoverlap_audit_v183 import evaluate as nonoverlap

SETTINGS=((6,6),(12,12),(18,18))
def evaluate(bars,settings=SETTINGS):
    if not settings:raise ValueError('EMPTY_SETTINGS')
    seen=set();cases=[]
    # Validate the complete configuration before processing any market history.
    for horizon,stride in settings:
        if not isinstance(horizon,int) or not isinstance(stride,int) or horizon<1 or stride<horizon:
            raise ValueError('INVALID_NONOVERLAP_SETTING')
        if (horizon,stride) in seen:raise ValueError('DUPLICATE_SETTING')
        seen.add((horizon,stride))
    for horizon,stride in settings:
        result=nonoverlap(bars,horizon=horizon,stride=stride)
        cases.append({'horizon_bars':horizon,'stride_bars':stride,
            'decision_windows_total':result['decision_windows_total'],
            'train':result['train'],'held_out':result['held_out']})
    return {'version':'alpha-1.8.4-btc-horizon-sensitivity',
        'asset':'BTC','timeframe':'4h','settings_predeclared':True,'cases':cases,
        'interpretation':'DESCRIPTIVE_SENSITIVITY_ONLY_NOT_PARAMETER_SELECTION',
        'limitations':['ONE_HISTORICAL_SLICE','NO_INDEPENDENT_PRICE_REGIMES',
           'MULTIPLE_LEVELS_SHARE_PRICE_PATH','NO_STATISTICAL_SIGNIFICANCE',
           'NO_SCORE_CALIBRATION','NO_EXECUTION_BACKTEST'],
        'research_only':True,'signals':[],'signals_enabled':False,
        'trading_enabled':False,'trade_authorized':False,
        'backtest_completed':False,'continuous_freshness_proven':False,
        'release_6_0_0_approved':False}
def main():
    report=evaluate(history_4h(pages=12))
    path=Path('artifacts/alpha_swing_v184_btc_horizon_sensitivity.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V184',json.dumps({'cases':[{'horizon':x['horizon_bars'],
      'train_windows':x['train']['decision_windows'],
      'held_out_windows':x['held_out']['decision_windows']} for x in report['cases']],
      'signals':0,'trades':0}))
if __name__=='__main__':main()
