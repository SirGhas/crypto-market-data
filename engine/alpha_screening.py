"""Alpha 0.3: rule-based research audit, never a trading signal."""
from decimal import Decimal, InvalidOperation

def positive(s):
    try:
        d=Decimal(str(s))
        return d if d.is_finite() and d>0 else None
    except (InvalidOperation,ValueError,TypeError):
        return None

def screen(snapshot):
    periods=('5m','15m','1h','4h')
    assets=('ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE','ZEC')
    result={
      'version':'alpha-0.3-screening-audit',
      'source_snapshot_version':snapshot.get('version'),
      'source_snapshot_time_utc':snapshot.get('timestamp_utc'),
      'research_only':True,'signals_enabled':False,'trading_enabled':False,
      'release_6_0_0_approved':False,'scores_computed':False,'signals':[],
      'continuous_freshness_proven':False,
      'scoring_tiers':{'green_min':80,'blue_min':70,'yellow_min':60},
      'scoring_policy':'NOT_COMPUTED: weighting and verified trade R/R unavailable',
      'rr_requirement':'at least 3 using validated entry, stop and target; illustrative R/R is insufficient',
      'assets':{},'totals':{}
    }
    total=0; data_valid=0; blocked=0; rvol_ge_1=0; breakouts=0
    for asset in assets:
        result['assets'][asset]={}
        for tf in periods:
            total+=1
            group=snapshot.get('timeframes',{}).get(tf,{})
            rel=group.get('relative_to_btc',{}).get(asset,{})
            diag=group.get('native_market_diagnostics',{}).get(asset,{})
            ok=(rel.get('status')=='VALIDATED_RELATIVE_CLOSE'
                and diag.get('status')=='RESEARCH_DIAGNOSTICS_ONLY'
                and rel.get('identity')==diag.get('identity')
                and rel.get('synthetic_volume') is None
                and rel.get('synthetic_liquidity') is None
                and diag.get('synthetic_volume') is None
                and diag.get('volume_is_native') is True
                and rel.get('signals_authorized') is False
                and diag.get('signal_authorized') is False)
            vol=positive(diag.get('relative_volume_20'))
            breakout=diag.get('breakout_close_above_resistance') is True
            if ok: data_valid+=1
            else: blocked+=1
            if ok and vol is not None and vol>=1:rvol_ge_1+=1
            if ok and breakout:breakouts+=1
            reasons=[]
            if not ok:reasons.append('DATA_OR_IDENTITY_UNVERIFIED')
            if ok and not breakout:reasons.append('NO_CONFIRMED_CLOSE_ABOVE_STATIC_RESISTANCE')
            if ok and (vol is None or vol<1):reasons.append('RELATIVE_VOLUME_BELOW_1_OR_INVALID')
            # A historical high is not a confirmed target. Hard fail-closed.
            reasons+=['VALIDATED_TRADE_ENTRY_STOP_TARGET_MISSING',
                      'CONTINUOUS_FRESHNESS_NOT_PROVEN',
                      'SCORE_POLICY_NOT_INTEGRATED',
                      'LIQUIDITY_SPREAD_DEPTH_NOT_VERIFIED']
            result['assets'][asset][tf]={
                'status':'RESEARCH_ONLY' if ok else 'BLOCKED',
                'data_valid':ok,'identity':rel.get('identity') if ok else None,
                'relative_close_btc':rel.get('relative_close_btc') if ok else None,
                'static_support_20':diag.get('static_support_20') if ok else None,
                'static_resistance_20':diag.get('static_resistance_20') if ok else None,
                'rvol20':str(vol) if ok and vol is not None else None,
                'rvol_ge_1':bool(ok and vol is not None and vol>=1),
                'close_above_resistance':bool(ok and breakout),
                'illustrative_rr_at_least_3':diag.get('illustrative_rr_at_least_3') if ok else None,
                'validated_trade_rr':None,'score':None,'tier':None,
                'signal_authorized':False,'blocking_reasons':reasons
            }
    result['totals']={'expected':total,'data_valid':data_valid,'blocked_data':blocked,
                      'rvol_ge_1':rvol_ge_1,'closes_above_resistance':breakouts,
                      'eligible_signals':0}
    result['outcome']='ALPHA_0_3_RESEARCH_SCREENING_ONLY'
    return result
