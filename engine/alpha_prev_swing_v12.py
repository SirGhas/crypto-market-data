"""Read-only download of last successful v1.2 report; no baseline on first run."""
import io,json,os,urllib.request,zipfile
from pathlib import Path

def main():
    repo=os.getenv('GITHUB_REPOSITORY');token=os.getenv('GITHUB_TOKEN')
    if not (repo and token):print('BASELINE_NOT_CONFIGURED');return
    h={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'alpha-v12'}
    url=f'https://api.github.com/repos/{repo}/actions/artifacts?name=alpha-swing-v12&per_page=50'
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=20) as r:data=json.load(r)
        candidates=sorted([v for v in data.get('artifacts',[]) if not v.get('expired') and str(v.get('workflow_run',{}).get('id'))!=os.getenv('GITHUB_RUN_ID')],key=lambda z:z.get('created_at',''),reverse=True)
        if not candidates:print('NO_PREVIOUS_BASELINE');return
        with urllib.request.urlopen(urllib.request.Request(candidates[0]['archive_download_url'],headers=h),timeout=30) as r:raw=r.read(15_000_000)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=[x for x in z.namelist() if x.endswith('alpha_swing_v12.json') and '..' not in x]
            if len(names)!=1:print('PREVIOUS_REPORT_NOT_FOUND');return
            obj=json.loads(z.read(names[0]))
        if obj.get('version')!='alpha-1.2-multi-timeframe-watch':print('INVALID_BASELINE_VERSION');return
        path=Path('artifacts/previous_alpha_swing_v12.json');path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf8');print('PREVIOUS_BASELINE_OK')
    except Exception as e:print('BASELINE_RETRIEVAL_FAILED',type(e).__name__,str(e)[:100])
if __name__=='__main__':main()
