"""本地只核验下载字节及准备记录，不执行方案数值校验或仿真。"""
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence'
REMOTE = EVIDENCE / 'remote'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(delivery):
    matched = []
    for row in delivery['files']:
        relative = Path(row['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        path = REMOTE / relative
        assert path.stat().st_size == row['size'] and sha(path) == row['sha256'], row['path']
        if len(relative.parts) == 1 and path.suffix in ('.py', '.sbatch', '.json', '.md'):
            assert sha(ROOT / relative) == row['sha256'], row['path']
            matched.append(row['path'])
    for name, digest in read(REMOTE/'preparation/inventory.json').items():
        assert sha(REMOTE/'preparation'/name) == digest, name
    return matched


def records():
    result = read(REMOTE/'preparation/result.json')
    plan = read(REMOTE/'protocol.proposed.json')
    claim = read(REMOTE/'preparation/claim.json')
    assert result['passed'] and result['plan_validated'] and not any(result['counts'].values())
    assert claim['kind'] == 'plan_verification' and claim['dynamics_budget_consumed'] == 0
    assert result['execution_authorized'] is result['entrypoint_ready'] is False
    assert result['proposed_budget'] == plan['proposed_budget']
    assert result['proposed_budget']['setup_steps'] == 0
    assert result['evidence']['baseline_fields'] == 626
    assert result['control']['commands'] == 1000
    assert result['semantics']['old_claim_consumed'] == 1
    assert result['semantics']['observation_qualified'] is False
    assert sha(REMOTE/'BINDINGS.json') == result['bindings_sha256']
    assert sha(REMOTE/'protocol.proposed.json') == result['protocol_sha256']
    assert not (REMOTE/'preparation/failure.json').exists()
    return result


def source_and_links():
    checked = []
    for path in ROOT.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text)
        lengths = [n.end_lineno-n.lineno+1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        assert len(text.splitlines()) <= 300 and max(lengths, default=0) <= 50
        checked.append(path.name)
    report = ROOT / 'REPORT.md'
    for target in re.findall(r'\]\(([^)]+)\)', report.read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#'):
            continue
        path = (ROOT / target).resolve()
        if path != (EVIDENCE/'FINAL_VERIFICATION.json').resolve():
            assert path.exists(), target
    for name in ('authorization.json', 'execute.sbatch', 'run'):
        assert not (ROOT/name).exists() and not (REMOTE/name).exists()
    return checked


def main():
    delivery = read(EVIDENCE/'DELIVERY.json')
    matched, result = files(delivery), records()
    report = dict(passed=True, files_verified=len(delivery['files']), local_source_files=matched,
        syntax_checked=source_and_links(), job=result['job'], counts=result['counts'],
        verified_server_identities=result['verified_identities'], plan_validated=True,
        execution_authorized=False, entrypoint_ready=False, dynamics_budget_consumed=0,
        no_simulator_executed_locally=True, production_ready=False)
    path = EVIDENCE/'FINAL_VERIFICATION.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    assert read(path) == report
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
