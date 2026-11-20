"""Full-system acceptance audit: explicit coverage, provenance, and failure gates."""
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

REQUIRED = (
    "market_ohlcv", "technical_trend", "momentum", "volume_liquidity",
    "multi_timeframe", "cross_asset", "macro", "geopolitics_news",
    "risk_management", "signal_decision", "alerts", "presentation",
    "historical_outcome",
)

def assess(components, cutoff):
    if cutoff.tzinfo is None:
        raise ValueError("CUTOFF_MUST_BE_TIMEZONE_AWARE")
    results = {}
    for name in REQUIRED:
        item=components.get(name)
        if not isinstance(item,dict):
            results[name]={"status":"FAIL","reason":"NOT_IMPLEMENTED_OR_NOT_CONNECTED"}
            continue
        if item.get("status")!="PASS":
            results[name]={"status":"FAIL","reason":str(item.get("reason","NOT_VERIFIED"))}
            continue
        try:
            observed=datetime.fromisoformat(item["as_of_utc"])
            if observed.tzinfo is None or observed.astimezone(timezone.utc)>cutoff.astimezone(timezone.utc):
                raise ValueError("FUTURE_OR_UNDATED_INPUT")
            if not item.get("evidence"):
                raise ValueError("MISSING_EVIDENCE")
            results[name]={"status":"PASS","reason":"VERIFIED_AT_CUTOFF","evidence":item["evidence"]}
        except (KeyError,ValueError,TypeError) as exc:
            results[name]={"status":"FAIL","reason":str(exc)}
    failed=[name for name,v in results.items() if v["status"]!="PASS"]
    return {"test":"FULL_ENGINE_HISTORICAL_ACCEPTANCE","cutoff_utc":cutoff.astimezone(timezone.utc).isoformat(),
            "verdict":"FAIL" if failed else "PASS","passed":len(REQUIRED)-len(failed),
            "total":len(REQUIRED),"failed_components":failed,"components":results,
            "execution_allowed":False}

def write_report(audit,folder):
    path=Path(folder)
    path.mkdir(parents=True,exist_ok=True)
    (path/"full_engine_acceptance.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    color="#b42318" if audit["verdict"]=="FAIL" else "#087f5b"
    rows="".join("<tr><td>"+escape(name)+"</td><td>"+escape(value["status"])+"</td><td>"+escape(value["reason"])+"</td></tr>" for name,value in audit["components"].items())
    html="""<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>آزمون پذیرش موتور تحلیل بازار</title><style>body{font-family:Tahoma,Arial,sans-serif;background:#101827;color:#edf2f7;margin:0;padding:24px}main{max-width:960px;margin:auto}.card{background:#1b283b;border-radius:14px;padding:22px;margin:16px 0}.verdict{color:COLOR;font-size:30px;font-weight:bold}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #34455a;text-align:right}tr:nth-child(even){background:#243449}.small{color:#aebed0}</style><main><h1>آزمون تمام‌عیار موتور تحلیل بازار</h1><section class="card"><p>تاریخ توقف داده‌ها: CUTOFF</p><p class="verdict">VERDICT</p><p>تعداد بخش‌های تأییدشده: PASSED از TOTAL</p><p class="small">عدم تأیید هر جزء، به معنی رد پذیرش کل موتور است؛ این گزارش سیگنال معاملاتی نیست.</p></section><section class="card"><h2>وضعیت تمام اجزا</h2><table><tr><th>بخش</th><th>وضعیت</th><th>دلیل</th></tr>ROWS</table></section></main></html>"""
    html=html.replace("COLOR",color).replace("CUTOFF",escape(audit["cutoff_utc"])).replace("VERDICT",escape(audit["verdict"])).replace("PASSED",str(audit["passed"])).replace("TOTAL",str(audit["total"])).replace("ROWS",rows)
    (path/"full_engine_acceptance.html").write_text(html,encoding="utf-8")
    return path

if __name__=="__main__":
    from datetime import timezone
    cutoff=datetime(2026,10,18,tzinfo=timezone.utc)
    audit=assess({},cutoff)
    write_report(audit,"artifacts/full-engine-acceptance")
    print(json.dumps({"verdict":audit["verdict"],"passed":audit["passed"],"total":audit["total"],"failed_components":audit["failed_components"]}))
