import ast
import importlib
import os
import unittest
from reflection.__main__ import bootstrap
bootstrap()
from collection_common import ROOT, save, sha


def main():
    assert os.environ.get('SLURM_JOB_ID')
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    modules = ('collect_worker','collect_audit','rc_prepare','rc_review','rc_controller','rc_qualification','rc_protocol')
    for name in modules:
        importlib.import_module(name)
    legacy = importlib.import_module('rc_common')
    assert 'container_recovery_v' in legacy.__file__, legacy.__file__
    for path in ROOT.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert len(text.splitlines()) <= 300, path
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno-node.lineno+1 <= 50, (path.name,node.name)
    paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md']
    save(ROOT/'verification.json', dict(passed=True, tests=tested.testsRun, imports=list(modules),
        physical_attempts=0, model_calls=0, identities={str(p):sha(p) for p in paths}))
    print(dict(passed=True, tests=tested.testsRun, imports=len(modules)), flush=True)


if __name__ == '__main__':
    main()
