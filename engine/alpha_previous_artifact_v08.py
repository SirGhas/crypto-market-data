"""Retrieve most recent earlier v0.8 run's raw v0.6 artifact using GitHub Actions read-only token."""
import io,json,os,urllib.request,zipfile
from pathlib import Path

def main():
    repo=os.environ.get('GITHUB_REPOSITORY');token=os.environ.get('GITHUB_TOKEN')
    if not repo or not token:
        print('NO_GITHUB_TOKEN_BASELINE_UNAVAILABLE');return
    api='https://api.github.com/repos/'+repo+'/actions/artifacts?name=alpha-research-integrity-v08&per_page=30'
    headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'research-alpha'}
    try:
        req=urllib.request.Request(api,headers=headers)
        with urllib.request.urlopen(req,timeout=20) as r:data=json.load(r)
        artifacts=[a for a in data.get('artifacts',[]) if not a.get('expired') and str(a.get('workflow_run',{}).get('id'))!=os.getenv('GITHUB_RUN_ID')]
        artifacts.sort(key=lambda a:a.get('created_at',''),reverse=True)
        if not artifacts:print('FIRST_RUN_NO_BASELINE');return
        req=urllib.request.Request(artifacts[0]['archive_download_url'],headers=headers)
        with urllib.request.urlopen(req,timeout=25) as r:body=r.read(20_000_000)
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            names=[n for n in z.namelist() if n.endswith('alpha_momentum_v06.json') and '../' not in n]
            if len(names)!=1:print('PREVIOUS_ARTIFACT_MISSING_V06');return
            previous=json.loads(z.read(names[0]))
        if previous.get('version')!='alpha-0.6-rsi-volume':print('PREVIOUS_BAD_VERSION');return
        p=Path('artifacts/previous_alpha_momentum_v06.json');p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(previous,ensure_ascii=False),encoding='utf8')
        print('PREVIOUS_BASELINE_FROM_RUN',previous.get('run_id'))
    except Exception as e:
        print('BASELINE_DOWNLOAD_FAILED',type(e).__name__,str(e)[:100])
if __name__=='__main__':main()
