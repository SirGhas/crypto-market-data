"""Point-in-time evidence from real OHLCV; no simulated factor inputs."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

def evidence_from_ohlcv(rows, cutoff, source):
    if cutoff.tzinfo is None:
        raise ValueError("NAIVE_CUTOFF")
    past=[]
    for r in rows:
        try:
            t=datetime.fromisoformat(r["closed_at_utc"])
            close=Decimal(str(r["close"]))
            high=Decimal(str(r["high"]))
            low=Decimal(str(r["low"]))
            volume=Decimal(str(r["volume"]))
        except (KeyError,TypeError,ValueError,InvalidOperation) as exc:
            raise ValueError("INVALID_OHLCV") from exc
        if t.tzinfo is None or not all(v.is_finite() for v in (close,high,low,volume)) or not (0<low<=close<=high and volume>=0):
            raise ValueError("INVALID_OHLCV")
        if t.astimezone(timezone.utc)<=cutoff.astimezone(timezone.utc):
            past.append((t,close,high,low,volume))
    past.sort(key=lambda x:x[0])
    if len({x[0] for x in past})!=len(past):
        raise ValueError("DUPLICATE_CANDLE")
    if len(past)<30:
        return {}
    closes=[r[1] for r in past]
    volumes=[r[4] for r in past]
    gains=[max(closes[i]-closes[i-1],Decimal(0)) for i in range(-14,0)]
    losses=[max(closes[i-1]-closes[i],Decimal(0)) for i in range(-14,0)]
    ag=sum(gains)/14
    al=sum(losses)/14
    rsi=Decimal(100) if al==0 else Decimal(100)-Decimal(100)/(Decimal(1)+ag/al)
    avgvol=sum(volumes[-20:])/20
    if avgvol<=0:
        return {}
    relative_volume=volumes[-1]/avgvol
    def item(metrics):
        return {"status":"PASS","as_of_utc":cutoff.isoformat(),
                "evidence":{"source":source,"last_closed_candle":past[-1][0].isoformat(),
                            "metrics":{k:str(v) for k,v in metrics.items()}}}
    return {
        "momentum":item({"rsi14":rsi,"last_close":closes[-1]}),
        "volume_liquidity":item({"volume":volumes[-1],"relative_volume_20":relative_volume,
                                  "note":"Volume evidence only; liquidity spread not independently verified"}),
        "multi_timeframe":item({"daily_sma5":sum(closes[-5:])/5,
                                "daily_sma20":sum(closes[-20:])/20,
                                "weekly_proxy_sma4":sum(closes[-28:])/28,
                                "note":"Weekly proxy from daily closes, not independent weekly feed"}),
    }
