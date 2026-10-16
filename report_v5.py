"""Event-only watchlist report. No buy orders, no notification transport."""
import datetime as dt,json,math
from pathlib import Path
ROOT=Path('data')
def read(name,default):
    try:return json.loads((ROOT/name).read_text(encoding='utf-8'))
    except (ValueError,FileNotFoundError):return default
def r(v,n=4):return round(v,n) if isinstance(v,(int,float)) and math.isfinite(v) else None
def analyze(coin,pairs,now):
    p=pairs.get(coin+'USDT',{});frames=p.get('frames',{})
    need=('4h','1h','15m')
    if any(frames.get(f,{}).get('status')!='available' for f in need):return {'coin':coin,'status':'blocked','reason':'missing_Binance_closed_candles'}
    h4=frames['4h']['candles'];h1=frames['1h']['candles'];m15=frames['15m']['candles']
    if any(not x for x in (h4,h1,m15)):return {'coin':coin,'status':'blocked','reason':'empty_candles'}
    # Binance close_ms is the last millisecond of a closed candle.
    if any(now-a[-1]['close_ms']>max_age for a,max_age in ((h4,5*3600000),(h1,2*3600000),(m15,3600000))):return {'coin':coin,'status':'blocked','reason':'stale_closed_candles'}
    price=p.get('last_trade_price');live_ok=price is not None and now-dt.datetime.fromisoformat(p['last_trade_price_time_utc']).timestamp()*1000<30*60000
    if not live_ok:price=h1[-1]['close']
    prior=h4[-21:-1]
    if len(prior)<20:return {'coin':coin,'status':'blocked','reason':'insufficient_4h_levels'}
    support=min(x['low'] for x in prior);resistance=max(x['high'] for x in prior)
    sma=sum(x['close'] for x in h4[-233:])/233
    prevvol=[x['volume'] for x in h1[-21:-1]]
    volratio=h1[-1]['volume']/(sum(prevvol)/len(prevvol)) if len(prevvol)==20 and sum(prevvol)>0 else None
    # Previous closed candle levels, never including the breakout candle.
    prior1=h1[-21:-1];breakout=bool(prior1 and h1[-1]['close']>max(x['high'] for x in prior1))
    cross=pairs.get(coin+'BTC',{}).get('frames',{}).get('4h',{})
    cross_ok=cross.get('status')=='available' and len(cross.get('candles',[]))>=233
    relative_positive=(cross['candles'][-1]['close']>sum(x['close'] for x in cross['candles'][-233:])/233) if cross_ok else None
    stop=support;target=resistance;risk=price-stop;reward=target-price
    rr=reward/risk if risk>0 and reward>0 else None
    trend=h4[-1]['close']>sma
    # Ranking is WATCH priority, not recommendation or valid trade score.
    score=(30 if trend else 0)+(25 if relative_positive else 0)+(20 if breakout else 0)+(15 if volratio is not None and volratio>=1.3 else 0)+(10 if rr is not None and rr>=2.5 else 0)
    reasons=[]
    if not trend:reasons.append('4h_below_sma233')
    if relative_positive is not True:reasons.append('relative_strength_not_confirmed')
    if not breakout:reasons.append('no_closed_1h_breakout')
    if volratio is None or volratio<1.3:reasons.append('volume_below_1_3x')
    if rr is None or rr<2.5:reasons.append('market_entry_RR_below_2_5')
    return {'coin':coin,'status':'watch' if not reasons else 'rejected','score':score,'price':r(price,8),'price_kind':'Binance_ticker_at_collection' if live_ok else 'last_closed_1h_candle','support_4h':r(support,8),'resistance_4h':r(resistance,8),'distance_above_support_pct':r((price/support-1)*100,2),'distance_below_resistance_pct':r((resistance/price-1)*100,2),'market_entry_RR':r(rr,2),'risk_pct_to_support':r((price-support)/price*100,2),'volume_ratio_1h':r(volratio,2),'above_sma233_4h':trend,'relative_strength_vs_BTC':relative_positive,'closed_1h_breakout':breakout,'reasons':reasons,'levels_method':'prior_20_closed_4h_candles_not_confirmed_static_levels'}
def main():
    data=read('binance_market.json',{});now=int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)
    generated=data.get('generated_at_utc');age=(now-dt.datetime.fromisoformat(generated).timestamp()*1000) if generated else float('inf')
    out={'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source':'Binance Spot public API','source_generated_at_utc':generated,'status':'unavailable','evaluations':[],'top_three_watchlist':[],'worst_market_entry':None,'new_events':[],'mode':'research_only_no_trades_no_push_notifications'}
    if age<=90*60000 and data.get('status')!='unavailable':
        out['evaluations']=[analyze(c,data.get('pairs',{}),now) for c in ('ETH','BNB','SOL','LTC','LINK','XRP','AVAX','SUI','AAVE')]
        ranked=sorted([x for x in out['evaluations'] if x['status']!='blocked'],key=lambda x:(x['score'],x['market_entry_RR'] or -1),reverse=True)
        out['top_three_watchlist']=ranked[:3]
        out['worst_market_entry']=min(ranked,key=lambda x:x['market_entry_RR'] if x['market_entry_RR'] is not None else -1) if ranked else None
        out['status']='available' if len(ranked)==9 else 'partial'
        # No event alerts without confirmed dominance and BTC structure validation.
    ROOT.mkdir(exist_ok=True)
    (ROOT/'report_v5.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':out['status'],'evaluated':len(out['evaluations']),'watchlist':len(out['top_three_watchlist'])}))
if __name__=='__main__':main()
