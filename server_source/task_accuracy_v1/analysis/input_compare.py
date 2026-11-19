"""只读核对同一首轮策略对照的实际点云和噪声深度。"""
import os
from pathlib import Path
import numpy as np
from ta_common import ROOT, PILOT, SEEDS, read, save, sha, verify

FIELDS = ('camera_points', 'world_points', 'depth', 'mask')


def main():
    manifest = verify(PILOT/'manifest.json')
    result = read(PILOT/'result.json')
    assert result['complete'] and result['counts']['audited_pairs'] == len(SEEDS)
    rows, identities = [], {}
    for seed in SEEDS:
        source = Path(manifest['references'][str(seed)]['step']).parent
        target = PILOT/'cases'/str(seed)/'first'
        paths = [source/'span_inputs.npz', target/'span_inputs.npz']
        with np.load(paths[0]) as old, np.load(paths[1]) as new:
            for field in FIELDS:
                np.testing.assert_array_equal(old[field], new[field], err_msg=f'{seed}: {field}')
            rows.append(dict(seed=seed, identical_fields=list(FIELDS), points=len(old['camera_points'])))
        identities.update({str(p): sha(p) for p in paths})
    save(ROOT/'analysis'/('result_'+os.environ['SLURM_JOB_ID']+'.json'),
        dict(passed=True, rows=rows, identities=identities, physical_attempts=0, model_calls=0))
    print(dict(passed=True, rows=rows), flush=True)


if __name__ == '__main__':
    main()
