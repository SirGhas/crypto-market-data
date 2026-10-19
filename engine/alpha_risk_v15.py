"""Alpha 1.5: conservative closed-candle ATR/pivot/R research overlay.

Never authorizes trades; rejects unsynchronised or incomplete exchange candles.
"""
from copy import deepcopy
from decimal import Decimal as D, InvalidOperation
import json
import urllib.parse
import urllib.request

VERSION = 'alpha-1.5-causal-risk-research'
OKX = 'https://www.okx.com/api/v5/market/candles'

def number(x):
    try:
        v = D(str(x))
        return v if v.is_finite() else None
    except (TypeError, ValueError, InvalidOperation):
        return None

def fmt(x):
    return format(x.quantize(D('0.00000001')).normalize(), 'f')

def get_closed_candles(asset, bar):
    """OKX: [ts,open,high,low,close,vol,...,confirm]. No live candle allowed."""
    url = OKX + '?' + urllib.parse.urlencode({'instId': asset+'-USDT', 'bar': bar, 'limit': '100'})
    req = urllib.request.Request(url, headers={'User-Agent': 'alpha-v15-research/1.0'})
    with urllib.request.urlopen(req, timeout=18) as r:
        obj = json.load(r)
    if obj.get('code') != '0':
        raise ValueError('EXCHANGE_RESPONSE_NOT_OK')
    rows = obj.get('data', [])
    seen = set(); out = []
    for row in rows:
        if len(row) < 9 or str(row[8]) != '1':
            continue
        ts = int(row[0]) // 1000
        if ts in seen:
            raise ValueError('DUPLICATE_CANDLE_TIMESTAMP')
        seen.add(ts)
        o,h,l,c = (number(row[i]) for i in (1,2,3,4))
        if any(v is None or v <= 0 for v in (o,h,l,c)) or l > min(o,c) or h < max(o,c):
            raise ValueError('INVALID_OHLC')
        out.append((ts,o,h,l,c))
    return sorted(out)

def validated_series(rows, identity, step_seconds):
    """Require report's last candle in trailing sequence; reject stale or future snapshots."""
    if not isinstance(identity, str) or ':' not in identity:
        raise ValueError('MISSING_REFERENCE_IDENTITY')
    expected = int(identity.split(':')[0]); duration = int(identity.split(':')[1])
    if duration * 60 != step_seconds:
        raise ValueError('REFERENCE_TIMEFRAME_MISMATCH')
    rows = [r for r in rows if r[0] <= expected]
    if not rows or rows[-1][0] != expected:
        raise ValueError('CLOSED_CANDLE_IDENTITY_MISMATCH')
    if len(rows) < 35 or any(b[0]-a[0] != step_seconds for a,b in zip(rows,rows[1:])):
        raise ValueError('INSUFFICIENT_CONTIGUOUS_CLOSED_HISTORY')
    return rows

def atr14(rows):
    tr=[]
    for i,(_,o,h,l,c) in enumerate(rows):
        prev = rows[i-1][4] if i else c
        tr.append(max(h-l, abs(h-prev), abs(l-prev)))
    if len(tr)<16: raise ValueError('INSUFFICIENT_ATR_HISTORY')
    val=sum(tr[1:15])/D(14)
    for t in tr[15:]:val=(val*D(13)+t)/D(14)
    return val

def confirmed_swing_low(rows, entry):
    candidates=[]
    for i in range(2,len(rows)-2):
        low=rows[i][3]
        if low < entry and all(low < rows[j][3] for j in (i-2,i-1,i+1,i+2)):
            candidates.append((rows[i][0],low))
    return candidates[-1] if candidates else None

def directional_reference(asset_obj):
    base=asset_obj.get('reference_score',{})
    p=asset_obj.get('timeframes',{}).get('4h',{})
    raw=number(base.get('score'))
    volume=number(base.get('parts',{}).get('native_volume'))
    if raw is None or volume is None:return {'status':'INVALID_SCORE','score':None}
    supportive = (p.get('status')=='VALIDATED' and p.get('candle_direction')=='UP'
                  and not p.get('broke_support_20') and number(p.get('rsi14')) is not None
                  and number(p['rsi14']) >= D('50') and
                  (p.get('broke_resistance_20') or (p.get('sma_close',{}).get('SMA233',{}).get('close_above')
                                                  and p.get('sma_close',{}).get('SMA233',{}).get('slope')=='UP')))
    excluded= D(0) if supportive else volume
    return {'status':'RESEARCH_DIRECTIONALLY_GATED','legacy_score':fmt(raw),
            'score':fmt(max(D(0),raw-excluded)),
            'native_volume_legacy_points':fmt(volume),'native_volume_excluded_points':fmt(excluded),
            'volume_bullish_confirmation':bool(supportive),
            'note':'Conservative research overlay; original reference_score preserved.'}

def risk_overlay(asset, baseline, risk_reference=None, get_candles=get_closed_candles):
    result=deepcopy(baseline)
    result['directional_reference_score']=directional_reference(baseline)
    old=risk_reference or {}
    out={'asset':asset,'status':'BLOCKED_UNVERIFIED_RISK','research_only':True,
         'reference_candle_4h':old.get('reference_candle'),'reference_candle_daily':old.get('daily_candle'),
         'atr14_4h':None,'atr14_daily':None,'confirmed_pivot_low_4h':None,
         'hypothetical_stop':None,'gross_risk_per_unit':None,'gross_risk_pct':None,
         'targets_by_R':{'2':None,'2.5':None,'3':None},'nearest_overhead_resistance':None,
         'gross_rr_to_resistance':None,'atr_buffer_multiplier':'0.5',
         'data_validation':{},'blocking_reasons':[], 'trade_authorized':False, 'signals_authorized':False}
    result['risk_v15']=out
    try:
        if not old or not old.get('reference_candle') or not old.get('daily_candle'):
            raise ValueError('MISSING_V14_RISK_REFERENCE')
        four=validated_series(get_candles(asset,'4H'),old['reference_candle'],14400)
        day=validated_series(get_candles(asset,'1Dutc'),old['daily_candle'],86400)
        expected4=number(baseline['timeframes']['4h']['close'])
        expectedD=number(baseline['timeframes']['1D']['close'])
        if four[-1][4]!=expected4 or day[-1][4]!=expectedD:
            raise ValueError('CANDLE_CLOSE_MISMATCH_WITH_REPORT')
        out['data_validation']={'ohlc_source':'OKX_SPOT_USDT','closed_4h':len(four),'closed_daily':len(day),
                                'matched_report_candle_identities':True}
        a4=atr14(four);ad=atr14(day)
        out['atr14_4h']=fmt(a4);out['atr14_daily']=fmt(ad)
        entry=expected4
        pivot=confirmed_swing_low(four,entry)
        if pivot is None:raise ValueError('NO_CONFIRMED_CAUSAL_SWING_LOW')
        out['confirmed_pivot_low_4h']={'epoch':pivot[0],'price':fmt(pivot[1])}
        stop=pivot[1]-D('0.5')*a4
        if not D(0)<stop<entry:raise ValueError('INVALID_HYPOTHETICAL_STOP')
        risk=entry-stop
        out['hypothetical_stop']=fmt(stop)
        out['gross_risk_per_unit']=fmt(risk)
        out['gross_risk_pct']=fmt(risk/entry*100)
        out['targets_by_R']={str(r):fmt(entry+r*risk) for r in (D('2'),D('2.5'),D('3'))}
        levels=[number(v) for k in ('4h_overhead_resistance_levels','daily_overhead_resistance_levels')
                for v in old.get(k,{}).values()]
        overhead=sorted({v for v in levels if v is not None and v>entry})
        if not overhead:raise ValueError('NO_VERIFIED_OVERHEAD_RESISTANCE')
        resistance=overhead[0]
        out['nearest_overhead_resistance']=fmt(resistance)
        out['gross_rr_to_resistance']=fmt((resistance-entry)/risk)
    except (ValueError,KeyError,IndexError,TypeError,TimeoutError, OSError) as exc:
        out['blocking_reasons'].append(str(exc).split(':')[0][:100])
    out['blocking_reasons']+=['LIVE_BID_ASK_SPREAD_NOT_VALIDATED',
                              'REALISTIC_FEES_SLIPPAGE_NOT_VALIDATED',
                              'WALK_FORWARD_BACKTEST_NOT_COMPLETED','RESEARCH_ONLY']
    return result

def overlay(report,get_candles=get_closed_candles):
    if report.get('version')!='alpha-1.4-structural-risk-research':
        raise ValueError('Expected Alpha 1.4 report')
    x=deepcopy(report);x['version']=VERSION
    x['assets']={a:risk_overlay(a,v,report.get('risk_research',{}).get(a,{}),get_candles) for a,v in report.get('assets',{}).items()}
    x['risk_v15']={a:v['risk_v15'] for a,v in x['assets'].items()}
    x['directional_research_scores']={a:v['directional_reference_score'] for a,v in x['assets'].items()}
    x['totals']=dict(x.get('totals',{}),atr_both_timeframes_validated=sum(bool(v['data_validation'].get('matched_report_candle_identities')) for v in x['risk_v15'].values()),trade_authorized=0)
    x.update(signals=[],signals_enabled=False,trading_enabled=False,research_only=True,
             release_6_0_0_approved=False,backtest_completed=False,continuous_freshness_proven=False)
    return x
