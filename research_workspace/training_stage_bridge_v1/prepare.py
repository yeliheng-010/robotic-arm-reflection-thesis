import os
import unittest
from pathlib import Path
from f_common import save, sha

ROOT = Path(__file__).resolve().parent
FOLDERS = ('training_stage_bridge_v1', 'visual_finetune_v1', 'visual_comparison_v1',
    'visual_dataset_audit_v1', 'visual_training_v1', 'visual_sft_v1')


def main():
    assert os.environ.get('SLURM_JOB_ID')
    import watch
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert result.wasSuccessful()
    paths = []
    for name in FOLDERS:
        folder = ROOT.parent/name
        paths.extend(p for p in folder.iterdir() if p.suffix in ('.py', '.sbatch', '.sh'))
    save(ROOT/'source_manifest.json', dict(tests=result.testsRun,
        identities={str(p): sha(p) for p in paths}, automatic_training_still_gated=True))


if __name__ == '__main__':
    main()
