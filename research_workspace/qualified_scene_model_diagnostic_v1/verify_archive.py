"""只核验已归档字节、报告引用与服务器记录，不执行数值实验。"""
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
EVIDENCE = ROOT / 'evidence'
REMOTE = EVIDENCE / 'remote'
FOLDERS = ('qualified_scene_candidate_v1', 'qualified_scene_candidate_audit_v1',
           'qualified_scene_model_diagnostic_v1', 'qualified_scene_static_audit_v2')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files_and_sources(delivery):
    sources, syntax = [], []
    for row in delivery['files']:
        path = REMOTE / row['path']
        assert path.is_relative_to(REMOTE) and '..' not in Path(row['path']).parts
        assert path.stat().st_size == row['size'] and sha(path) == row['sha256'], row['path']
        relative = Path(row['path'])
        if len(relative.parts) == 2 and path.suffix in ('.py', '.sbatch', '.md', '.json'):
            local = PROJECT / relative
            if local.exists():
                assert sha(local) == row['sha256'], str(local)
                sources.append(row['path'])
    for folder in FOLDERS:
        for path in (PROJECT / folder).glob('*.py'):
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source)
            lengths = [n.end_lineno-n.lineno+1 for n in ast.walk(tree)
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            assert len(source.splitlines()) <= 300 and max(lengths, default=0) <= 50, str(path)
            syntax.append(str(path.relative_to(PROJECT)))
    return dict(files_verified=len(delivery['files']), local_sources_verified=sources, syntax_checked=syntax)


def records():
    scene = REMOTE / FOLDERS[0]
    failed = REMOTE / FOLDERS[1]
    diagnostic = REMOTE / FOLDERS[2]
    static = REMOTE / FOLDERS[3]
    assert 'Unbound imported files' in read(scene/'run/failure.json')['error']
    assert read(failed/'run/failure.json')['error'] == 'ValueError: Reloaded model fields differ'
    assert not (scene/'run/result.json').exists() and not (failed/'run/result.json').exists()
    diff, audit = read(diagnostic/'run/result.json'), read(static/'run/result.json')
    assert diff['diagnostic_completed'] and audit['passed'] and audit['static_geometry_passed']
    assert not audit['identity']['original_exact_audit_passed']
    assert audit['identity']['serialized_fields_matched'] == 625
    assert audit['tests'] == 7 and not diff['observation']['observation_qualified']
    for row in (diff, audit, read(scene/'run/failure.json'), read(failed/'run/failure.json')):
        assert all(row['counts'][key] == 0 for key in
                   ('integration', 'environment_step', 'close', 'planning', 'optimizer'))
    for folder in (diagnostic, static):
        for name, digest in read(folder/'run/inventory.json').items():
            assert sha(folder/'run'/name) == digest, name
    assert not (scene/'run/observation/qualified_sensor.npz').exists()
    return dict(original_failures_preserved=True, original_exact_audit_passed=False,
                static_serialized_identity_audit_passed=True, observation_qualified=False)


def references():
    checked = []
    for folder in FOLDERS:
        path = PROJECT / folder / 'REPORT.md'
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            target = target.split('#')[0]
            if (path.parent / target).resolve() == (EVIDENCE/'FINAL_VERIFICATION.json').resolve():
                continue  # 本次核验最后生成的唯一输出，写入后再次检查。
            assert (path.parent / target).exists(), (str(path), target)
        checked.append(str(path.relative_to(PROJECT)))
    return checked


def main():
    delivery = read(EVIDENCE/'DELIVERY.json')
    result = dict(**files_and_sources(delivery), **records(), reports_checked=references())
    binary = delivery['remote_only'][0]
    audit = read(REMOTE/FOLDERS[3]/'run/result.json')
    assert binary['sha256'] == audit['model_sha256'] and binary['size'] == audit['model_size']
    assert not (REMOTE/binary['path']).exists()
    result.update(remote_only=delivery['remote_only'], simulator_executed_locally=False,
                  production_ready=False, dynamics_validated=False)
    (EVIDENCE/'FINAL_VERIFICATION.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    assert read(EVIDENCE/'FINAL_VERIFICATION.json') == result
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
