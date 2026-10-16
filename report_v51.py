"""Conservative market-entry ranking, not trade signals."""
import datetime as dt,json,math
from pathlib import Path
ROOT=Path('data')
COINS=('BTC','ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE')
def pct(x): return round(x*100,3)
def analyze(coin, pairs):
    p=pairs.get(coin+'USDT',{}).get('frames',{})
    required=('4h','1h','15m')
    if any(p.get(f,{}).get('status')!='available' for f in required):
        return {'coin':coin,'status':'blocked','reasons':['missing_spot_closed_candles'],'sources':{f:p.get(f,{}).get('source') for f in required}}
    h=p['4h']['candles']; h1=p['1h']['candles']; m15=p['15m']['candles']
    price=h1[-1]['c']; prior=h[-21:-1]
    support=min(x['l'] for x in prior); resistance=max(x['h'] for x in prior)
    # A last-close reference, not a live trade price.
    sma=sum(x['c'] for x in h[-233:])/233
    volavg=sum(x['v'] for x in h1[-21:-1])/20
    volratio=h1[-1]['v']/volavg if volavg>0 else None
    cross=pairs.get(coin+'BTC',{}).get('frames',{}).get('4h',{}) if coin!='BTC' else None
    relgood=None
    if cross and cross.get('status')=='available':
        c=cross['candles']; relgood=c[-1]['c']>sum(x['c'] for x in c[-233:])/233
    risk=price-support; reward=resistance-price
    rr=round(reward/risk,3) if risk>0 and reward>0 else None
    reasons=[]
    if price<=sma: reasons.append('below_4h_sma233')
    if volratio is None or volratio<1.3: reasons.append('volume_not_confirmed')
    if relgood is False: reasons.append('weak_against_btc')
    if relgood is None and coin!='BTC': reasons.append('btc_pair_unavailable')
    if rr is None or rr<2.5: reasons.append('market_entry_rr_below_2_5')
    if not (m15[-1]['c']>sum(x['c'] for x in m15[-233:])/233): reasons.append('15m_below_sma233')
    # Ranking rewards strong relative trend and proximity to support, but no buy authorization.
    score=(25 if price>sma else 0)+(20 if relgood else 0)+(15 if volratio is not None and volratio>=1.3 else 0)+(20 if rr is not None and rr>=2.5 else 0)+(10 if m15[-1]['c']>sum(x['c'] for x in m15[-233:])/233 else 0)+(10 if risk>0 and price/support-1<0.04 else 0)
    return {'coin':coin,'status':'watch_only' if reasons else 'candidate_requires_manual_confirmation','score':score,'reference_price_usdt':price,'reference_price_kind':'last_closed_1h_candle_not_live','support_4h':support,'resistance_4h':resistance,'distance_above_support_percent':pct(price/support-1),'distance_below_resistance_percent':pct(resistance/price-1),'market_entry_rr':rr,'risk_percent_to_support':pct(risk/price) if risk>0 else None,'reward_percent_to_resistance':pct(reward/price) if reward>0 else None,'relative_volume_1h':round(volratio,3) if volratio is not None else None,'above_4h_sma233':price>sma,'relative_strength_btc':relgood,'reasons':reasons,'sources':{f:p[f]['source'] for f in required},'closed_1h_at_utc':p['1h']['last_closed_at_utc'],'notes':'20 prior 4h candle range is provisional, not verified multi-touch static levels; RR excludes fees/slippage'}
def main():
    d=json.loads((ROOT/'multisource_market.json').read_text()); evaluations=[analyze(c,d['pairs']) for c in COINS]
    ranked=sorted([x for x in evaluations if x['status']!='blocked' and x['coin']!='BTC'],key=lambda x:(x['score'],x['market_entry_rr'] if x['market_entry_rr'] is not None else -1),reverse=True)
    worst=min(ranked,key=lambda x:(x['market_entry_rr'] if x['market_entry_rr'] is not None else -1,x['score'])) if ranked else None
    out={'schema_version':51,'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source_generated_at_utc':d['generated_at_utc'],'status':d['summary']['status'],'mode':'research_only_no_trade_or_push','evaluations':evaluations,'top_three_watchlist':ranked[:3],'worst_market_entry':worst,'new_events':[],'disclaimer':'No verified static level, dominance trend, or 4h breakout/reclaim confirmation. Ranking is not a buy signal.'}
    (ROOT/'report_v51.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({'status':out['status'],'ranked':len(ranked),'top':[x['coin'] for x in ranked[:3]]}))
if __name__=='__main__': main()
