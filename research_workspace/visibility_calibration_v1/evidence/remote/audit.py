from pathlib import Path
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from surface_grasp_v1.common import read,save,sha
from surface_physical_v1.common import verify
from held_observation_v1.geometry import estimate
from visibility_calibration_v1.fitting import single,pair

ROOT=Path(__file__).resolve().parent


def load(folder,index,*,repeat):
    path=folder/f'view_{index}'
    assert sha(path/'clouds.npz')==read(path/'metadata.json')['clouds_sha256']
    with np.load(path/'clouds.npz') as data:
        return data[f'noise_{repeat}'].copy()


def phase(folder):
    results=read(folder/'fits.json')
    # 预先固定首/中/末样本，不按真值正确性挑选。
    checked=[]
    rows=results['pairs']
    chosen=sorted(set([0,len(rows)//2,len(rows)-1])) if rows else []
    for index in chosen:
        row=rows[index]
        clouds=[load(folder,i,repeat=row['repeat']) for i in row['indices']]
        value=pair(*clouds,fits=[single(c) for c in clouds])
        expected={k:v for k,v in row.items() if k not in ('indices','repeat')}
        assert expected==value
        original=estimate(clouds,np.eye(4))
        assert original['quality_passed']==value['quality_passed']
        if value['quality_passed']:
            np.testing.assert_array_equal(original['center_world_m'],value['fit']['center'])
        checked.append(dict(indices=row['indices'],repeat=row['repeat'],identical=True))
    return dict(pair_checks=checked,scope='first_middle_last_not_full_replay')


def main():
    verify(ROOT/'manifest.json')
    for path,digest in read(ROOT/'completed.json')['outputs'].items():
        assert sha(path)==digest,path
    results={name:phase(ROOT/'phases'/name) for name in ('preflight','after_lift','before_release')}
    save(ROOT/'audit.json',dict(passed=True,phases=results,all_saved_output_hashes_verified=True,
        physical_success_verified=False,task_motion_attempts=0))
    print(results,flush=True)


if __name__=='__main__':
    main()
