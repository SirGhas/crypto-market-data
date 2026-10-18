"""Process the existing real v0.6 artifact without another exchange API request."""
import argparse,json
from pathlib import Path
from engine.alpha_scoring_v07 import analyze
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',default='artifacts/alpha_momentum_v06.json')
    p.add_argument('--output',default='artifacts/alpha_scoring_v07.json')
    a=p.parse_args()
    output=analyze(json.loads(Path(a.input).read_text(encoding='utf8')))
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(output['totals'])
if __name__=='__main__':main()
