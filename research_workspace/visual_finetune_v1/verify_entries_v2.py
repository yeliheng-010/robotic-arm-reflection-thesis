"""同时保留旧导入顺序反例与新入口实际路径证据。"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    assert os.environ.get('SLURM_JOB_ID')
    prior = subprocess.run([sys.executable, '-B', '-c',
        'import freeze,smoke,train; print(smoke.__file__); print(train.__file__)'],
        check=True, capture_output=True, text=True, cwd=ROOT)
    assert '/candidate_sft_v2/smoke.py' in prior.stdout
    assert '/candidate_sft_v2/train.py' in prior.stdout
    print('CONFIRMED_OLD_ENTRY_COLLISION '+prior.stdout.strip(), flush=True)
    import freeze_v2
    import smoke_v2
    import train_v2
    import vf_common_v2
    for module in (freeze_v2, smoke_v2, train_v2, vf_common_v2):
        assert Path(module.__file__).resolve().parent == ROOT
        print('VERIFIED_NEW_ENTRY '+module.__file__, flush=True)
    assert train_v2.probe is smoke_v2.probe
    assert vf_common_v2.runtime.__file__.endswith('/candidate_sft_v2/runtime.py')
    assert sys.modules['loss'].__file__.endswith('/candidate_sft_v2/loss.py')
    print('All active v2 entries use multimodal probe; zero real model loading or updates', flush=True)


if __name__ == '__main__':
    main()
