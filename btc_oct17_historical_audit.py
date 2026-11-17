"""Point-in-time BTC daily historical benchmark; public market data, paper only."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from paired_historical_benchmark import compare
from full_engine_acceptance import assess, write_report
from ohlcv_factor_evidence import evidence_from_ohlcv

CUTOFF=datetime(2026,10,18,0,0,0,tzinfo=timezone.utc)
START_MS=int(datetime(2026,9,1,tzinfo=timezone.utc).timestamp()*1000)
END_MS=int(datetime(2026,11,10,tzinfo=timezone.utc).timestamp()*1000)
SOURCES=[
    "https://api.binance.com/api/v3/klines",
    "https://api.binance.us/api/v3/klines",
]
def fetch():
    from urllib.parse import urlencode
    errors=[]
    for source in SOURCES:
        url=source+"?"+urlencode({"symbol":"BTCUSDT","interval":"1d","startTime":START_MS,"endTime":END_MS,"limit":200})
        try:
            with urlopen(Request(url,headers={"User-Agent":"market-audit/1"}),timeout=20) as response:
                rows=json.load(response)
            if not isinstance(rows,list) or not rows or not all(isinstance(x,list) and len(x)>=7 for x in rows):
                raise ValueError("INVALID_KLINES")
            candles=[{"closed_at_utc":datetime.fromtimestamp((int(r[6])+1)/1000,timezone.utc).isoformat(),
                      "close":str(r[4]),"high":str(r[2]),"low":str(r[3]),"volume":str(r[5])} for r in rows]
            if not any(datetime.fromisoformat(c["closed_at_utc"]).date().isoformat()=="2026-10-18" for c in candles):
                raise ValueError("CUTOFF_DATE_NOT_IN_DATA")
            return source,candles
        except Exception as exc:
            errors.append(source+": "+type(exc).__name__+": "+str(exc)[:100])
    raise RuntimeError("ALL_HISTORICAL_SOURCES_FAILED: "+"; ".join(errors))

def main():
    path=Path("artifacts/btc_2026_10_17_historical_audit.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    output={"asset":"BTCUSDT","cutoff_date":"2026-10-17","mode":"HISTORICAL_PAPER_ONLY",
            "execution_allowed":False,"status":"BLOCKED"}
    try:
        source,candles=fetch()
        result=compare(candles,CUTOFF,factors=None,fast=5,slow=20,horizon=4,fee_bps=10)
        observed=CUTOFF.isoformat()
        components=evidence_from_ohlcv(candles,CUTOFF,source)
        components["market_ohlcv"]={"status":"PASS","as_of_utc":observed,
                    "evidence":{"source":source,"past_candles":result["baseline"]["past_candles"]}}
        if result["baseline"]["past_candles"]>=21:
            components["technical_trend"]={"status":"PASS","as_of_utc":observed,
                "evidence":{"strategy":"SMA_CROSSOVER_BASELINE",
                            "signal":result["baseline"]["signal"]}}
        components["signal_decision"]={"status":"FAIL","reason":"MULTIFACTOR_ENGINE_NOT_CONNECTED"}
        components["historical_outcome"]={"status":"FAIL","reason":"NO_EVALUABLE_SIGNAL_OR_INSUFFICIENT_VALIDATION"}
        audit=assess(components,CUTOFF)
        write_report(audit,"artifacts/full-engine-acceptance")
        output["acceptance"]={"verdict":audit["verdict"],"passed":audit["passed"],
                              "total":audit["total"],"failed_components":audit["failed_components"]}
        output.update({"source":source,"data_candles":len(candles),"result":result,
                       "status":"EVALUATED" if result["baseline"]["evaluated"] else "NO_EVALUABLE_SIGNAL"})
    except Exception as exc:
        output["reason"]=str(exc)[:400]
    if "acceptance" not in output:
        audit=assess({},CUTOFF)
        write_report(audit,"artifacts/full-engine-acceptance")
        output["acceptance"]={"verdict":audit["verdict"],"passed":audit["passed"],
                              "total":audit["total"],"failed_components":audit["failed_components"]}
    path.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(output,ensure_ascii=False))
    if output["status"]=="BLOCKED":
        raise SystemExit(2)

if __name__=="__main__":
    main()
