#!/usr/bin/env python3
"""Compare two actual Kraken/OKX snapshots, research-only. Never emits a signal."""
import argparse
import datetime as datetime
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

PERIOD = {'5m':300,'15m':900,'1h':3600,'4h':14400}
SOURCES = ('kraken','okx_reference')

def get_decimal(value):
    try:
        x=Decimal(str(value))
        if x.is_finite() and x>0:return x
    except (InvalidOperation,ValueError,TypeError):pass
    raise ValueError('INVALID_POSITIVE_VALUE')

def iso_timestamp(s):
    return int(datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp())

def assess(before,after,tf,source,previous_run,new_run):
    period=PERIOD[tf]
    entry={'source':source,'previous_identity':None,'current_identity':None,'status':'UNVERIFIED','identity_advanced':False,
           'new_closed_candle_due':None,'price_changed':None,'fresh_against_runner_clock':False,'reasons':[]}
    if not isinstance(before,dict) or not isinstance(after,dict):
        entry['reasons'].append('MISSING_SOURCE_SNAPSHOT');return entry
    try:
        a=int(before['start_epoch']);b=int(after['start_epoch']); now=iso_timestamp(new_run)
        old_at=iso_timestamp(previous_run)
        entry['previous_identity']=before.get('identity');entry['current_identity']=after.get('identity')
        if entry['previous_identity']!=f'{a}:{period//60}' or entry['current_identity']!=f'{b}:{period//60}':
            entry['reasons'].append('IDENTITY_INCONSISTENT');return entry
        if a%period!=0 or b%period!=0: entry['reasons'].append('MISALIGNED_EPOCH');return entry
        if now<=old_at:entry['reasons'].append('RUN_TIMESTAMP_NOT_ADVANCED');return entry
        if a+period>old_at or b+period>now:entry['reasons'].append('UNFINISHED_CANDLE');return entry
        # Most recent CLOSED candle at time of current snapshot. No future inference.
        most_recent=(now//period-1)*period
        entry['new_closed_candle_due']=most_recent>a
        entry['identity_advanced']=b>a
        entry['fresh_against_runner_clock']=(b==most_recent)
        old_price=get_decimal(before['synthetic_zec_btc']);new_price=get_decimal(after['synthetic_zec_btc'])
        entry['price_changed']=old_price!=new_price
        if b<a:entry['reasons'].append('CANDLE_REGRESSION')
        if b==a and entry['new_closed_candle_due']:entry['reasons'].append('STALE_IDENTITY_AFTER_CLOSE')
        if b>most_recent:entry['reasons'].append('FUTURE_CANDLE')
        if b<most_recent:entry['reasons'].append('LATEST_CLOSED_CANDLE_MISSING')
        if after.get('synthetic_volume') is not None or after.get('synthetic_liquidity') is not None:
            entry['reasons'].append('SYNTHETIC_VOLUME_OR_LIQUIDITY_PRESENT')
        if after.get('fresh') is not True:entry['reasons'].append('CURRENT_SOURCE_NOT_FRESH')
        if not entry['reasons']:
            entry['status']='ADVANCED_VERIFIED' if b>a else 'UNCHANGED_NOT_DUE'
            if not entry['price_changed'] and b>a:entry['reasons'].append('UNCHANGED_PRICE_WITH_NEW_CANDLE_IS_PERMITTED')
        else:entry['status']='BLOCKED'
    except (KeyError,ValueError,TypeError,InvalidOperation,OverflowError) as ex:
        entry['reasons'].append('SNAPSHOT_VALIDATION_ERROR:'+str(ex)[:100]);entry['status']='BLOCKED'
    return entry

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline',default='tests/fixtures/kraken_okx_baseline_v5115.json')
    p.add_argument('--current',default='artifacts/kraken_okx_cross_probe_v5115.json')
    p.add_argument('--out',default='artifacts/kraken_okx_freshness_comparison_v5116.json')
    args=p.parse_args()
    previous=json.loads(Path(args.baseline).read_text(encoding='utf-8'))
    current=json.loads(Path(args.current).read_text(encoding='utf-8'))
    report={'probe_version':'5.11.6','phase':'03_cross_run_freshness_validation',
        'baseline_timestamp_utc':previous.get('timestamp_utc'), 'current_timestamp_utc':current.get('timestamp_utc'),
        'baseline_run_id':previous.get('github',{}).get('run_id'),'current_run_id':current.get('github',{}).get('run_id'),
        'research_only':True,'trading_enabled':False,'signals_enabled':False,
        'exchange_admission_authorized':False,'synthetic_signal_authorized':False,'release_6_0_0_approved':False,
        'comparison_is_two_snapshots_only':True,'continuous_freshness_proven':False,'source_results':{},'outcome':'BLOCKED'}
    ok=True
    if previous.get('github',{}).get('repository')!=current.get('github',{}).get('repository'):
        ok=False;report['repository_warning']='DIFFERENT_REPOSITORY'
    if previous.get('github',{}).get('run_id')==current.get('github',{}).get('run_id'):
        ok=False;report['same_run_warning']='SAME_RUN_ID'
    for tf in PERIOD:
        result={}
        for source in SOURCES:
            old=previous.get('intervals',{}).get(tf,{}).get(source)
            new=current.get('intervals',{}).get(tf,{}).get(source)
            item=assess(old,new,tf,source,previous['timestamp_utc'],current['timestamp_utc'])
            result[source]=item
            if item['status'] not in ('ADVANCED_VERIFIED','UNCHANGED_NOT_DUE'):ok=False
        k=result['kraken'];o=result['okx_reference']
        result['cross_source_timestamp_aligned']=(k['current_identity']==o['current_identity'] and k['current_identity'] is not None)
        if not result['cross_source_timestamp_aligned']:ok=False
        new_entry=current.get('intervals',{}).get(tf,{})
        result['diagnostic_eligible']=new_entry.get('diagnostic_eligible') is True
        result['divergence_percent']=new_entry.get('divergence_percent')
        if not result['diagnostic_eligible']:ok=False
        report['source_results'][tf]=result
    report['outcome']='SNAPSHOT_ADVANCE_VALIDATED_RESEARCH_ONLY' if ok else 'BLOCKED'
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Saved',out,report['outcome'])

if __name__=='__main__':main()
