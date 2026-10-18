import argparse,json
from pathlib import Path
from engine.alpha_integrity_v08 import analyze

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--scoring',default='artifacts/alpha_scoring_v07.json')
    p.add_argument('--momentum',default='artifacts/alpha_momentum_v06.json')
    p.add_argument('--previous',default='artifacts/previous_alpha_momentum_v06.json')
    p.add_argument('--output',default='artifacts/alpha_integrity_v08.json')
    a=p.parse_args();read=lambda x:json.loads(Path(x).read_text(encoding='utf-8'))
    prev=read(a.previous) if Path(a.previous).exists() else None
    result=analyze(read(a.scoring),read(a.momentum),prev)
    target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print({'cross_run':result['cross_run']['status'],'events_reported':result['event_summary']['events_reported'],
           'embargo_selected':result['event_summary']['events_embargo_selected']})
    if result['cross_run']['status']=='ANOMALY_DETECTED':raise SystemExit('CROSS_RUN_ANOMALY')
if __name__=='__main__':main()
