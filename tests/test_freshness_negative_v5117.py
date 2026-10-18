#!/usr/bin/env python3
"""Offline adversarial tests for existing v5.11.6 comparison logic. No network or signals."""
import copy, importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('comparison',Path(__file__).with_name('compare_cross_snapshots_v5116.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
base=json.loads((ROOT/'tests/fixtures/kraken_okx_baseline_v5115.json').read_text())
current=json.loads((ROOT/'tests/fixtures/kraken_okx_current_v5116.json').read_text())
old_run=base['timestamp_utc']; new_run=current['timestamp_utc']

def item(src,tf='5m'):
    return copy.deepcopy(base['intervals'][tf][src]),copy.deepcopy(current['intervals'][tf][src])

def check(name, tf, mutate, wanted, src='kraken', reason=None):
    before,after=item(src,tf)
    mutate(before,after)
    got=m.assess(before,after,tf,src,old_run,new_run)
    good=got['status']==wanted and (not reason or any(reason in x for x in got['reasons']))
    return dict(test=name,pass_test=good,expected=wanted,actual=got['status'],reasons=got['reasons'])

results=[]
results.append(check('real_5m_advances','5m',lambda a,b:None,'ADVANCED_VERIFIED'))
results.append(check('real_4h_not_due','4h',lambda a,b:None,'UNCHANGED_NOT_DUE'))
results.append(check('stale_5m','5m',lambda a,b:b.update(start_epoch=a['start_epoch'],identity=a['identity']), 'BLOCKED',reason='STALE_IDENTITY_AFTER_CLOSE'))
results.append(check('regressed_5m','5m',lambda a,b:b.update(start_epoch=a['start_epoch']-300,identity=f"{a['start_epoch']-300}:5"),'BLOCKED',reason='CANDLE_REGRESSION'))
results.append(check('bad_identity','5m',lambda a,b:b.update(identity='bad'),'BLOCKED',reason='IDENTITY_INCONSISTENT'))
results.append(check('bad_alignment','5m',lambda a,b:b.update(start_epoch=b['start_epoch']+2,identity=f"{b['start_epoch']+2}:5"),'BLOCKED',reason='MISALIGNED_EPOCH'))
results.append(check('native_false_fresh','5m',lambda a,b:b.update(fresh=False),'BLOCKED',reason='CURRENT_SOURCE_NOT_FRESH'))
results.append(check('invented_liquidity','5m',lambda a,b:b.update(synthetic_liquidity='100'),'BLOCKED',reason='SYNTHETIC_VOLUME_OR_LIQUIDITY_PRESENT'))
results.append(check('invented_volume','5m',lambda a,b:b.update(synthetic_volume='10'),'BLOCKED',reason='SYNTHETIC_VOLUME_OR_LIQUIDITY_PRESENT'))
results.append(check('missing_price','5m',lambda a,b:b.pop('synthetic_zec_btc'),'BLOCKED',reason='SNAPSHOT_VALIDATION_ERROR'))
results.append(check('missing_source','5m',lambda a,b:b.clear(),'BLOCKED'))
results.append(check('unchanged_price_advancing','5m',lambda a,b:b.update(synthetic_zec_btc=a['synthetic_zec_btc']),'ADVANCED_VERIFIED'))
report={'probe_version':'5.11.7','phase':'04_offline_negative_safety_tests','research_only':True,'signals_enabled':False,'trading_enabled':False,'exchange_admission_authorized':False,'synthetic_signal_authorized':False,'release_6_0_0_approved':False,'tests':results,'passed':sum(x['pass_test'] for x in results),'total':len(results),'outcome':'NEGATIVE_TESTS_PASSED' if all(x['pass_test'] for x in results) else 'BLOCKED'}
out=ROOT/'artifacts/freshness_negative_tests_v5117.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
print(report['outcome'],report['passed'],'/',report['total'])
if report['outcome']=='BLOCKED':raise SystemExit(1)
