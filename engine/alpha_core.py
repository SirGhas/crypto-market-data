"""Strict, dependency-free research data validation and relative-close mathematics."""
from decimal import Decimal, InvalidOperation

BARS = {'5m': (300, '5m'), '15m': (900, '15m'), '1h': (3600, '1H'), '4h': (14400, '4H')}
COINS = ('ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE','ZEC')

class InvalidMarketData(ValueError):
    pass

def decimal_positive(value):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidMarketData('INVALID_NUMBER') from exc
    if not d.is_finite() or d <= 0:
        raise InvalidMarketData('NON_POSITIVE_OR_NON_FINITE')
    return d

def parse_okx_rows(payload, timeframe, now_epoch):
    if timeframe not in BARS: raise InvalidMarketData('UNSUPPORTED_TIMEFRAME')
    period, _ = BARS[timeframe]
    if not isinstance(payload, dict) or str(payload.get('code')) != '0' or not isinstance(payload.get('data'), list):
        raise InvalidMarketData('API_RESPONSE_INVALID')
    rows = {}
    for raw in payload['data']:
        if not isinstance(raw, list) or len(raw) < 9: continue
        try:
            start_ms = int(raw[0]); start, fraction = divmod(start_ms, 1000)
            if fraction or start % period or start > now_epoch or start + period > now_epoch: continue
            if str(raw[8]) != '1': continue
            op,hi,lo,cl = (decimal_positive(raw[i]) for i in (1,2,3,4))
            vol = Decimal(str(raw[5]))
            if not vol.is_finite() or vol < 0 or hi < max(op,cl,lo) or lo > min(op,cl,hi): continue
            candidate = {'start_epoch':start,'close':cl,'open':op,'high':hi,'low':lo,'base_volume':vol}
            if start in rows and candidate != rows[start]: raise InvalidMarketData('DUPLICATE_CONFLICT')
            rows[start] = candidate
        except InvalidMarketData as exc:
            if str(exc) == 'DUPLICATE_CONFLICT': raise
            continue
        except (ValueError, TypeError, InvalidOperation):
            continue
    return rows

def relative_close(alt_rows, btc_rows, timeframe, now_epoch):
    if timeframe not in BARS: raise InvalidMarketData('UNSUPPORTED_TIMEFRAME')
    period, _ = BARS[timeframe]
    expected_start = (now_epoch // period - 1) * period
    if expected_start not in alt_rows or expected_start not in btc_rows:
        return {'status':'BLOCKED', 'reason':'LATEST_CLOSED_CANDLE_MISSING','identity':f'{expected_start}:{period//60}'}
    alt=alt_rows[expected_start];btc=btc_rows[expected_start]
    ratio = decimal_positive(alt['close']) / decimal_positive(btc['close'])
    return {'status':'VALIDATED_RELATIVE_CLOSE', 'identity':f'{expected_start}:{period//60}',
            'start_epoch':expected_start, 'relative_close_btc':format(ratio,'.12f'),
            'alt_usdt_close':str(alt['close']), 'btc_usdt_close':str(btc['close']),
            'alt_native_volume':str(alt['base_volume']), 'btc_native_volume':str(btc['base_volume']),
            'synthetic_volume':None, 'synthetic_liquidity':None,
            'direct_pair_ohlc_verified':False, 'direct_pair_liquidity_verified':False,
            'signals_authorized':False}
