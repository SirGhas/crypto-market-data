"""Causal BTC 4H resistance walk-forward research; strictly no trades or signals.

Historical candidates built using only bars closed by a decision timestamp.
Future six 4H candles are used ONLY to label outcomes, never to rank levels.
"""
import json,time,urllib.parse,urllib.request
from decimal import Decimal as D
from pathlib import Path
from engine.alpha_body_levels_v168 import extract,number,parse

def history_4h(pages=5,transport=None,now=None):
    now=int(time.time()) if now is None else int(now)
    raw=[];cursor=None;seen=set()
    for _ in range(pages):
        args={'instId':'BTC-USDT','bar':'4H','limit':'100'}
        if cursor is not None:args['after']=str(cursor)
        url='https://www.okx.com/api/v5/market/history-candles?'+urllib.parse.urlencode(args)
        if transport:payload=transport(url)
        else:
            req=urllib.request.Request(url,headers={'User-Agent':'alpha-walkforward-v171/1.0'})
            with urllib.request.urlopen(req,timeout=20) as f:payload=json.load(f)
        if payload.get('code')!='0' or not isinstance(payload.get('data'),list):
            raise ValueError('OKX_HISTORY_ERROR')
        rows=payload['data']
        if not rows:break
        new=0
        for row in rows:
            if len(row)<9:raise ValueError('BAD_HISTORY_ROW')
            stamp=int(row[0])
            if stamp not in seen:
                seen.add(stamp);raw.append(row);new+=1
        older=min(int(r[0]) for r in rows)
        if cursor is not None and older>=cursor:raise ValueError('HISTORY_PAGINATION_STALLED')
        cursor=older
        if not new:break
    # Causal OHLCV validation, chronology, contiguous closed history via shared parser.
    return parse(raw,'4h',now)

def rank_candidates(snapshot):
    levels=[]
    for z in snapshot['candidates']:
        if z['type']!='resistance':continue
        piv=int(z['body_pivot_count'])
        events=z['events']
        volume=sum(1 for e in events if number(e['candle_rvol20']) is not None and number(e['candle_rvol20'])>=D('1.5'))
        strength=sum(min(number(e['response_atr']),D(3)) for e in events)
        score=D(min(piv,5)*10+min(len(events),4)*12+min(volume,3)*4)+min(strength,D(5))*D(3)
        levels.append((score,number(z['body_level']),z))
    levels.sort(key=lambda x:(-x[0],x[1]))
    return levels

def label_future(level,atr,future):
    """Observe first approach; no inferred sequence within a 4H candle."""
    threshold=atr*D('.3')
    for i,bar in enumerate(future):
        t,o,h,l,c,v=bar
        if h<level:return 'NO_TOUCH' if i==len(future)-1 else None
        if c>=level+atr*D('.15'):return 'BREAKOUT_CLOSE'
        if c<level and i+2<len(future):
            nexttwo=future[i+1:i+3]
            low=min(x[3] for x in nexttwo)
            maxclose=max(x[4] for x in nexttwo)
            if low<=level-threshold and maxclose<level+atr*D('.15'):
                return 'REJECTION_OBSERVED'
            return 'TOUCH_NO_CONFIRMED_REJECTION'
        return 'TOUCH_UNRESOLVED'
    return 'NO_TOUCH'

def classify(level,atr,future):
    for i,b in enumerate(future):
        if b[2]<level:continue
        if b[4]>=level+atr*D('.15'):return 'BREAKOUT_CLOSE'
        if i+2>=len(future):return 'TOUCH_UNRESOLVED'
        two=future[i+1:i+3]
        if any(x[4]>=level+atr*D('.15') for x in two) and min(x[3] for x in two)<=level-atr*D('.3'):
            return 'AMBIGUOUS_BOTH_DIRECTIONS'
        if any(x[4]>=level+atr*D('.15') for x in two):return 'BREAKOUT_CLOSE'
        if min(x[3] for x in two)<=level-atr*D('.3'):
            return 'REJECTION_OBSERVED'
        return 'TOUCH_NO_CONFIRMED_REJECTION'
    return 'NO_TOUCH'

def walkforward(bars,lookback=90,horizon=6,stride=6):
    if len(bars)<lookback+horizon+stride*2:raise ValueError('INSUFFICIENT_WALKFORWARD_HISTORY')
    if any(b[0]-a[0]!=14400 for a,b in zip(bars,bars[1:])):
        raise ValueError('NON_CONTIGUOUS_WALKFORWARD_DATA')
    rows=[]
    for stop in range(lookback,len(bars)-horizon+1,stride):
        past=bars[stop-lookback:stop]
        future=bars[stop:stop+horizon]
        # Extract uses only historical past; no future access.
        snap=extract('4h',past)
        candidates=rank_candidates(snap)
        if not candidates:
            rows.append({'decision_epoch':past[-1][0]+14400,'status':'NO_RESISTANCE_CANDIDATE'})
            continue
        atr=number(snap['atr14_simple_research'])
        high=candidates[0];near=min(candidates,key=lambda z:z[1])
        record={'decision_epoch':past[-1][0]+14400,'status':'EVALUATED',
                'past_last_closed_epoch':past[-1][0],
                'future_first_epoch':future[0][0],
                'future_last_epoch':future[-1][0],
                'historical_close':snap['last_close'],'atr_4h':snap['atr14_simple_research'],
                'highest_score_level':str(high[1]),'highest_score':str(high[0]),
                'nearest_level':str(near[1]),'nearest_score':str(near[0]),
                'high_score_outcome':classify(high[1],atr,future),
                'nearest_outcome':classify(near[1],atr,future),
                'same_level':high[1]==near[1]}
        rows.append(record)
    def metrics(prefix):
        outcomes=[r[prefix+'_outcome'] for r in rows if r.get('status')=='EVALUATED']
        return {'evaluations':len(outcomes),
                'touched':sum(x!='NO_TOUCH' for x in outcomes),
                'confirmed_rejections':outcomes.count('REJECTION_OBSERVED'),
                'breakout_closes':outcomes.count('BREAKOUT_CLOSE'),
                'ambiguous':outcomes.count('AMBIGUOUS_BOTH_DIRECTIONS'),
                'unresolved':outcomes.count('TOUCH_UNRESOLVED'),
                'touched_without_confirmed_rejection':outcomes.count('TOUCH_NO_CONFIRMED_REJECTION'),
                'no_touch':outcomes.count('NO_TOUCH')}
    result={'version':'alpha-1.7.1-btc-causal-walkforward','asset':'BTC','timeframe':'4h',
         'historical_closed_bars':len(bars),'decision_lookback_bars':lookback,
         'future_horizon_bars':horizon,'stride_bars':stride,
         'top_ranked_heuristic':metrics('high_score'),'nearest_candidate':metrics('nearest'),
         'evaluations':rows,
         'method_limits':['NO_OUT_OF_SAMPLE_SCORE_CALIBRATION','HISTORICAL_REPLAY_NOT_LIVE_PROOF',
             'ONE_CANDLE_INTRABAR_SEQUENCE_UNKNOWN','SAME_MARKET_PATH_BOTH_COMPARATORS',
             'NO_TRADE_BY_PRICE_FLOW','PIVOT_HEURISTIC_UNVALIDATED'],
         'research_only':True,'signals':[],'signals_enabled':False,'trading_enabled':False,
         'trade_authorized':False,'backtest_completed':False,'continuous_freshness_proven':False}
    return result

def main():
    bars=history_4h()
    data=walkforward(bars)
    path=Path('artifacts/alpha_swing_v171_btc.json')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ALPHA_V171',json.dumps({'bars':len(bars),'comparators':['top_ranked_heuristic','nearest_candidate'],
         'evaluation_count':len(data['evaluations']),'signals':0,'trades':0}))
if __name__=='__main__':main()
