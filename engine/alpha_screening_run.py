#!/usr/bin/env python3
"""Use existing alpha v0.2 live collector once, then screen its artifact."""
import json, subprocess, sys
from pathlib import Path
from engine.alpha_screening import screen

def main():
    subprocess.run([sys.executable,'engine/alpha_diagnostic_run.py'],check=True)
    src=Path('artifacts/alpha_diagnostics_v02.json')
    snapshot=json.loads(src.read_text(encoding='utf-8'))
    audit=screen(snapshot)
    target=Path('artifacts/alpha_screening_v03.json')
    target.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Alpha audit:',audit['totals'], 'signals enabled:',audit['signals_enabled'])

if __name__=='__main__':
    main()
