"""Read-only audit of transitive local engine imports, without executing market code."""
import ast
import json
from pathlib import Path

ENTRY = 'engine.alpha_swing_run_v161'

def audit(root=Path('.'), entry=ENTRY):
    root = Path(root)
    visited = set()
    missing = set()
    errors = {}
    def check(name):
        if name in visited:
            return
        visited.add(name)
        file = root.joinpath(*name.split('.')).with_suffix('.py')
        if not file.is_file():
            missing.add(str(file.relative_to(root)))
            return
        try:
            tree = ast.parse(file.read_text(encoding='utf-8'))
            deps = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith('engine.')]
            deps += [alias.name for n in ast.walk(tree) if isinstance(n, ast.Import) for alias in n.names if alias.name.startswith('engine.')]
            for dep in sorted(set(deps)):
                check(dep)
        except (OSError, SyntaxError, UnicodeError) as exc:
            errors[name] = str(exc)
    check(entry)
    return {'status': 'READY' if not missing and not errors else 'BLOCKED', 'checked_modules': sorted(visited), 'missing_files': sorted(missing), 'errors': errors, 'research_only': True, 'signals_enabled': False, 'trading_enabled': False}

def main():
    result = audit()
    out = Path('artifacts/alpha_dependency_preflight.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
    raise SystemExit(0 if result['status'] == 'READY' else 2)

if __name__ == '__main__':
    main()
