"""只读测量运行时几何缓存与qpos重建之间的差异。"""
import os
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import read,save
from goal_inputs import ROOT
from route_audit_v3 import rebuild
from goal_geometry import geometry


def main():
    assert os.environ.get('SLURM_JOB_ID')
    results=[]
    for case in read(ROOT/'manifest.json')['cases']:
        if case['reused_success']:
            continue
        trace=read(ROOT/'physics'/case['id']/'route.json')
        flow=rebuild(case,trace)
        current=geometry(flow,case['item'])
        expected=trace['endpoints']['geometry']
        differences={k:(np.array(current[k])-np.array(expected[k])).tolist() for k in expected}
        maximum=max(float(np.max(np.abs(v))) for v in differences.values())
        row=dict(id=case['id'],recorded=expected,reconstructed=current,differences=differences,max_abs_m=maximum)
        results.append(row)
        print(case['id'],maximum,differences,flush=True)
    save(ROOT/'geometry_diagnostic.json',results)


if __name__=='__main__':
    main()
