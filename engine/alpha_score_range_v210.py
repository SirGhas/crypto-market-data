"""Alpha 2.1.0: audit attainable score ranges and exact-score outcome distributions."""
from collections import Counter
from engine.alpha_importance_v179 import score_level, TF_WEIGHT
from engine.alpha_score_audit_v180 import evaluate as replay

def attainable():
    return {tf: sorted({score_level(tf,p,r) for p in range(4) for r in range(3)}) for tf in TF_WEIGHT}

def summarize(events):
    groups={}
    for e in events:
        key=str(e["heuristic_score"])
        g=groups.setdefault(key,{"outcomes":Counter(),"windows":set()})
        g["outcomes"][e["outcome"]]+=1
        g["windows"].add(e["decision_epoch"])
    return {k:{"outcomes":dict(v["outcomes"]),"decision_windows":len(v["windows"])}
            for k,v in sorted(groups.items(),key=lambda x:int(x[0]))}

def evaluate(bars):
    ranges=attainable()
    boundary=bars[len(bars)*7//10][0]
    events=replay(bars)["events"]
    if any(e["heuristic_score"] not in ranges["4h"] for e in events):
        raise ValueError("UNATTAINABLE_SCORE")
    return {"version":"alpha-2.1.0","attainable_scores":ranges,
            "high_band_reachable_4h":max(ranges["4h"])>=60,
            "earlier":summarize([e for e in events if e["decision_epoch"]+12*14400<=boundary]),
            "holdout":summarize([e for e in events if e["decision_epoch"]>=boundary]),
            "weights_changed":False,"research_only":True,"signals_enabled":False,
            "trading_enabled":False,"trade_authorized":False,"backtest_completed":False,
            "limitations":["DESCRIPTIVE_ONLY","REUSED_HOLDOUT_NOT_INDEPENDENT","CORRELATED_OBSERVATIONS"]}
