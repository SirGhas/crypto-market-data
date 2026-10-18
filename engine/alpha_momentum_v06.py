"""Close-only Wilder RSI and native-volume/price-action audit. Research-only."""
from decimal import Decimal
from engine.alpha_core import BARS


def rsi_wilder(rows, timeframe, now_epoch, length=14):
    period = BARS[timeframe][0]
    last = (now_epoch // period - 1) * period
    # 100 closed values gives 85 smoothing updates; all causal, contiguous.
    times = [last-i*period for i in range(99,-1,-1)]
    if any(t not in rows for t in times):
        return {'status':'BLOCKED','reason':'RSI_CONTIGUOUS_HISTORY_MISSING'}
    closes = [rows[t]['close'] for t in times]
    if any(not isinstance(c,Decimal) or not c.is_finite() or c<=0 for c in closes):
        return {'status':'BLOCKED','reason':'INVALID_CLOSE'}
    changes = [closes[i]-closes[i-1] for i in range(1,len(closes))]
    gain = sum((max(x,Decimal(0)) for x in changes[:length]),Decimal(0))/length
    loss = sum((max(-x,Decimal(0)) for x in changes[:length]),Decimal(0))/length
    values=[]
    def point(g,l):
        if g==0 and l==0:return Decimal(50)
        if l==0:return Decimal(100)
        return Decimal(100)-Decimal(100)/(Decimal(1)+g/l)
    values.append(point(gain,loss))
    for x in changes[length:]:
        gain=(gain*(length-1)+max(x,Decimal(0)))/length
        loss=(loss*(length-1)+max(-x,Decimal(0)))/length
        values.append(point(gain,loss))
    current, previous = values[-1], values[-2]
    return {'status':'RSI_WILDER_CLOSE_VALIDATED','identity':f'{last}:{period//60}',
            'period':length,'source':'CLOSE','value':str(current),'previous':str(previous),
            'momentum_50':'ABOVE' if current>50 else 'BELOW' if current<50 else 'EQUAL',
            'crossed_above_50':previous<=50<current,
            'crossed_below_50':previous>=50>current,
            'above_70':current>=70,'below_30':current<=30,
            'signals_authorized':False}


def volume_price_action(rows, timeframe, now_epoch):
    period=BARS[timeframe][0];last=(now_epoch//period-1)*period
    if any((last-i*period) not in rows for i in range(21)):
        return {'status':'BLOCKED','reason':'NATIVE_VOLUME_HISTORY_MISSING'}
    cur=rows[last];hist=[rows[last-i*period] for i in range(1,21)]
    necessary=('open','high','low','close','base_volume')
    if any(k not in candle for candle in [cur,*hist] for k in necessary):
        return {'status':'BLOCKED','reason':'NATIVE_FIELDS_MISSING'}
    v=cur['base_volume']; avg=sum((c['base_volume'] for c in hist),Decimal(0))/20
    if avg<=0:return {'status':'BLOCKED','reason':'ZERO_VOLUME_BASELINE'}
    high=max(c['high'] for c in hist);low=min(c['low'] for c in hist)
    span=cur['high']-cur['low']
    location=(cur['close']-cur['low'])/span if span>0 else None
    direction='UP' if cur['close']>cur['open'] else 'DOWN' if cur['close']<cur['open'] else 'FLAT'
    return {'status':'NATIVE_VOLUME_PRICE_ACTION_VALIDATED','identity':f'{last}:{period//60}',
            'candle_direction':direction,'close_location_in_range':str(location) if location is not None else None,
            'rvol20':str(v/avg),'rvol_ge_1':v>=avg,'rvol_ge_1_5':v>=avg*Decimal('1.5'),
            'rvol_ge_2':v>=avg*2,'closed_above_prior_resistance_20':cur['close']>high,
            'closed_below_prior_support_20':cur['close']<low,
            'volume_source':'OKX_NATIVE_BASE_VOLUME', 'synthetic_volume':None,
            'signals_authorized':False}
