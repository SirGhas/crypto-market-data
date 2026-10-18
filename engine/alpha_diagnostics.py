"""Research-only deterministic support/resistance, volume, and RR diagnostics.
Does not compute trading scores or authorize signals.
"""
from decimal import Decimal


def diagnose(rows, timeframe, now_epoch, period, lookback=20, target_lookback=60):
    expected=(now_epoch//period-1)*period
    # Only trailing consecutive *closed* candles ending at expected timestamp.
    times=[expected-i*period for i in range(target_lookback+1)]
    if any(t not in rows for t in times):
        return {'status':'BLOCKED','reason':'INSUFFICIENT_CONTIGUOUS_CLOSED_HISTORY','required_candles':target_lookback+1}
    current=rows[expected]
    prev=[rows[expected-i*period] for i in range(1,lookback+1)]
    extended=[rows[expected-i*period] for i in range(1,target_lookback+1)]
    resistance=max(x['high'] for x in prev)
    support=min(x['low'] for x in prev)
    avg_vol=sum((x['base_volume'] for x in prev),Decimal(0))/Decimal(lookback)
    vol_ratio=current['base_volume']/avg_vol if avg_vol>0 else None
    # Target is previous longer-window high; breakout lacks valid long target in this naive model.
    target=max(x['high'] for x in extended)
    entry=current['close']; risk=entry-support; reward=target-entry
    rr=reward/risk if risk>0 and reward>0 else None
    return {
      'status':'RESEARCH_DIAGNOSTICS_ONLY','timeframe':timeframe,
      'identity':f'{expected}:{period//60}',
      'close':str(entry),'static_support_20':str(support),
      'static_resistance_20':str(resistance),'prior_high_60':str(target),
      'breakout_close_above_resistance':entry>resistance,
      'breakdown_close_below_support':entry<support,
      'native_volume':str(current['base_volume']),
      'average_native_volume_20':str(avg_vol),
      'relative_volume_20':str(vol_ratio) if vol_ratio is not None else None,
      'illustrative_long_rr_to_prior_high_60':str(rr) if rr is not None else None,
      'illustrative_rr_at_least_3':rr>=3 if rr is not None else None,
      'rr_usable_for_signals':False,
      'volume_is_native':True,'synthetic_volume':None,
      'signal_authorized':False,
      'notes':'Static historical boundaries; not a validated entry, stop or target. No scores or signals.'
    }
