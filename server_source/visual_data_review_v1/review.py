import os
import unittest
from pathlib import Path
from f_common import save, sha
from vd_collect import collect, summarize, metrics

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_safe_visual_loop_v1'


def main():
    assert os.environ.get('SLURM_JOB_ID')
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    rows, conditions, identities = collect(SOURCE)
    paths = [*ROOT.glob('*.py'), SOURCE/'manifest.json', SOURCE/'complete.json']
    identities.update({str(p):sha(p) for p in paths})
    value = dict(summary=summarize(rows), metrics=metrics(conditions), rows=rows, conditions=conditions,
        tests=tested.testsRun, manifest_sha256=sha(SOURCE/'manifest.json'), identities=identities)
    save(ROOT/'inventory.json', value)
    print(dict(summary=value['summary'], metrics=value['metrics']), flush=True)


if __name__ == '__main__':
    main()
