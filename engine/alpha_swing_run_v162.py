"""Alpha 1.6.2: isolated 11-asset research run, BTC as asset and market benchmark.
Does not mutate repository-wide COINS or enable trading/signals.
"""
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from engine import alpha_core
from engine.alpha_swing_run_v161 import main as collect_v161

EXPECTED_ALTS = ('AAVE','AVAX','BNB','ETH','LINK','LTC','SOL','SUI','XRP','ZEC')
UNIVERSE = tuple(sorted(('BTC',) + EXPECTED_ALTS))
VERSION = 'alpha-1.6.2-btc-benchmark-research'

def positive(value):
    try:
        d=Decimal(str(value))
        return d if d.is_finite() and d>0 else None
    except (TypeError, ValueError, InvalidOperation):
        return None

def benchmark_overlay(raw):
    assets=raw.get('assets',{})
    if set(assets)!=set(UNIVERSE):
        raise ValueError('FAIL_CLOSED_UNIVERSE_NOT_11')
    btc=assets['BTC']
    for tf in ('4h','1D'):
        if btc.get('timeframes',{}).get(tf,{}).get('status')!='VALIDATED':
            raise ValueError('FAIL_CLOSED_BTC_REFERENCE_'+tf)
    result=dict(raw)
    result['version']=VERSION
    result['asset_universe']=list(UNIVERSE)
    result['benchmark_asset']='BTC'
    result['benchmark_quote']='USDT'
    result['benchmark_timeframes']=['4h','1D']
    result['benchmark_role']='INDEPENDENT_RESEARCH_ASSET_AND_SHARED_MARKET_REFERENCE'
    result['btc_relative_price_research']={}
    for asset in UNIVERSE:
        if asset=='BTC':continue
        item=assets[asset]
        comparison={'status':'NOT_VALIDATED','timeframes':{},'limitations':[
            'RELATIVE_PRICE_LEVEL_NOT_RELATIVE_PERFORMANCE',
            'NO_INDEPENDENT_BTC_OUTPERFORMANCE_BACKTEST',
            'NATIVE_SPOT_USDT_VOLUME_NOT_CROSS_ASSET_COMPARABLE',
            'NO_SYNTHETIC_BTC_PAIR_LIQUIDITY']}
        ok=True
        for tf in ('4h','1D'):
            a=item.get('timeframes',{}).get(tf,{})
            b=btc['timeframes'][tf]
            aa=positive(a.get('close'));bb=positive(b.get('close'))
            match=a.get('identity')==b.get('identity')
            if a.get('status')!='VALIDATED' or not match or aa is None or bb is None:
                comparison['timeframes'][tf]={'status':'BLOCKED','reason':'CLOSED_CANDLE_IDENTITY_OR_PRICE_MISMATCH'}
                ok=False
            else:
                comparison['timeframes'][tf]={
                    'status':'VALIDATED_SYNCHRONIZED_RELATIVE_PRICE',
                    'identity':a['identity'],'alt_usdt_close':str(aa),'btc_usdt_close':str(bb),
                    'relative_price_in_btc':format(aa/bb,'.12f'),
                    'direct_alt_btc_order_book_verified':False}
        if ok: comparison['status']='SYNCHRONIZED_SPOT_RELATIVE_PRICE_RESEARCH'
        result['btc_relative_price_research'][asset]=comparison
    result['totals']=dict(result.get('totals',{}),assets=11,btc_independently_validated=1,
                          benchmark_comparisons_validated=sum(v['status']=='SYNCHRONIZED_SPOT_RELATIVE_PRICE_RESEARCH'
                                                              for v in result['btc_relative_price_research'].values()),
                          trade_authorized=0,signals=0)
    result.update(signals=[],signals_enabled=False,trading_enabled=False,
                  release_6_0_0_approved=False,continuous_freshness_proven=False,
                  backtest_completed=False,research_only=True,trade_authorized=False)
    return result

def main():
    previous=alpha_core.COINS
    if set(previous)!=set(EXPECTED_ALTS):
        raise RuntimeError('FAIL_CLOSED_UNEXPECTED_BASE_UNIVERSE')
    try:
        alpha_core.COINS=UNIVERSE
        # Runner imports COINS by name at import time, so update its binding only in this process.
        from engine import alpha_swing_run_v12
        previous_runner=alpha_swing_run_v12.COINS
        alpha_swing_run_v12.COINS=UNIVERSE
        try:
            collect_v161()
        finally:
            alpha_swing_run_v12.COINS=previous_runner
    finally:
        alpha_core.COINS=previous
    source=Path('artifacts/alpha_swing_v161.json')
    report=benchmark_overlay(json.loads(source.read_text(encoding='utf-8')))
    output=Path('artifacts/alpha_swing_v162.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V162',json.dumps({
        'assets':len(report['assets']),
        'btc_validated':report['totals']['btc_independently_validated'],
        'benchmark_comparisons_validated':report['totals']['benchmark_comparisons_validated'],
        'ohlcv_observed_assets':report['totals'].get('observed_evidence_assets'),
        'signals':0,'trading_enabled':False}))

if __name__=='__main__':
    main()
