"""Research-only historical event study, strict forward horizon/no look-ahead."""
from decimal import Decimal
from engine.alpha_core import BARS

HORIZONS=(1,3,6,12)

def event_study(rows, timeframe, now_epoch):
    period=BARS[timeframe][0]
    final=(now_epoch//period-1)*period
    starts=sorted(rows)
    report={'status':'BLOCKED','timeframe':timeframe,'method':'NON_OVERLAPPING_CAUSAL_EVENT_STUDY',
            'signals_authorized':False,'backtest_completed':False,'trade_pnl_computed':False,
            'sma_windows':[20,50,233],'sma_source':'CLOSE','horizons_candles':list(HORIZONS),
            'events':[],'counts':{'breakout':0,'breakdown':0}}
    if not starts or starts[-1]!=final:
        report['reason']='LATEST_CLOSED_CANDLE_UNAVAILABLE'; return report
    # Every event requires SMA233 slope (234 closes) + 20 prior bars + forward 12 bars.
    required=234+max(HORIZONS)
    if len(starts)<required:
        report['reason']='INSUFFICIENT_HISTORY';report['required_candles']=required;return report
    if any(starts[i]-starts[i-1]!=period for i in range(1,len(starts))):
        report['reason']='NONCONTIGUOUS_HISTORY';return report
    closes=[rows[t]['close'] for t in starts]
    highs=[rows[t]['high'] for t in starts]
    lows=[rows[t]['low'] for t in starts]
    vols=[rows[t]['base_volume'] for t in starts]
    events=[]
    for idx in range(233,len(starts)-max(HORIZONS)):
        last20=slice(idx-20,idx)
        high20=max(highs[last20]);low20=min(lows[last20])
        avg=sum(vols[last20],Decimal(0))/20
        if avg<=0: continue
        rvol=vols[idx]/avg
        if rvol<1:continue  # purely disclosed observational filter
        direction='breakout' if closes[idx]>high20 else 'breakdown' if closes[idx]<low20 else None
        if direction is None: continue
        sma20=sum(closes[idx-19:idx+1],Decimal(0))/20
        sma50=sum(closes[idx-49:idx+1],Decimal(0))/50
        sma233=sum(closes[idx-232:idx+1],Decimal(0))/233
        previous233=sum(closes[idx-233:idx],Decimal(0))/233
        # Snapshot computed using only data known at event close.
        forward={}
        for horizon in HORIZONS:
            change=(closes[idx+horizon]/closes[idx]-1)*100
            forward[str(horizon)]={'raw_return_pct':str(change),
                  'direction_aligned_pct':str(change if direction=='breakout' else -change)}
        events.append({'candle_id':f'{starts[idx]}:{period//60}',
                       'direction':direction,'rvol20':str(rvol),
                       'event_close':str(closes[idx]),'sma20':str(sma20),
                       'sma50':str(sma50),'sma233':str(sma233),
                       'sma233_slope':'UP' if sma233>previous233 else 'DOWN' if sma233<previous233 else 'FLAT',
                       'above_sma233':closes[idx]>sma233,'forward':forward})
    report['status']='RESEARCH_EVENT_STUDY_VALID'
    report['usable_event_positions']=max(0,len(starts)-max(HORIZONS)-233)
    report['closed_history_count']=len(starts)
    report['counts']={'breakout':sum(e['direction']=='breakout' for e in events),
                      'breakdown':sum(e['direction']=='breakdown' for e in events)}
    report['events']=events
    report['note']='No fees, spreads, entries, stops, targets, fills or trade PnL; NOT a trading backtest.'
    return report
