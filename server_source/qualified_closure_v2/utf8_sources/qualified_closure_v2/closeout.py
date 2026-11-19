"""冻结新版本证据，保留v1不兼容结果和原6732失败。"""
import ast
import os
import subprocess
from qualified_closure_v2.common import ROOT, RUN, read, save, sha, verify


def source_checks():
    paths = list(ROOT.glob('*.py')) + list((ROOT.parent / 'qualified_closure_v1').glob('*.py'))
    callbacks = []
    for path in paths:
        content = path.read_text(encoding='utf-8')
        assert len(content.splitlines()) <= 300, path
        for node in ast.walk(ast.parse(content)):
            if not isinstance(node, ast.FunctionDef):
                continue
            assert node.end_lineno - node.lineno + 1 <= 50, (path, node.name)
            if len(node.args.args) > 3:
                assert path.name == 'adapter.py' and node.name == 'evaluate'
                callbacks.append(str(path.relative_to(ROOT.parent)) + ':evaluate')
    return dict(files=len(paths), external_four_argument_callbacks=callbacks)


def main():
    frozen = verify()
    positive = read(RUN / 'positive.json')
    assert positive['passed'] and positive['physical_close_calls'] == 0
    positive_sources = read(RUN / 'positive_manifest.json')['sources']
    assert all(sha(name) == digest for name, digest in positive_sources.items())
    audit = read(RUN / 'audit.json')
    assert audit['passed'] and audit['integration']['physical_close_calls'] == 0
    closure = read(RUN / 'closure.json')
    assert not closure['passed'] and closure['envelope_collisions'] > 0
    assert read(ROOT.parent / 'qualified_execution_v1/run/attempt_claim.json')['consumed'] == 1
    identities = {}
    active = 'closeout-' + os.environ['SLURM_JOB_ID'] + '.log'
    for directory in (ROOT.parent / 'qualified_closure_v1', ROOT):
        for path in directory.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.name != active:
                identities[str(path.relative_to(ROOT.parent))] = sha(path)
    accounting = subprocess.run(['sacct', '-j', '6797,6798,6799,6800,6801',
                                 '--format=JobID,State,ExitCode,Elapsed', '-n', '-P'],
                                check=True, capture_output=True, text=True).stdout
    result = dict(passed=True, source_checks=source_checks(), identities=identities,
                  frozen_sources=len(frozen['sources']), frozen_previous_files=len(frozen['originals']),
                  positive_sources=len(positive_sources), job_accounting=accounting,
                  original_exact_audit_passed=False, physical_attempts=0, model_calls=0, training_runs=0)
    save(RUN / 'delivery_inventory.json', result)
    print({k: v for k, v in result.items() if k != 'identities'}, flush=True)


if __name__ == '__main__':
    main()
