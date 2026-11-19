from pathlib import Path
from reflection.__main__ import bootstrap
bootstrap()
from surface_grasp_v1.common import read,save,sha
from surface_physical_v1.common import verify
from visibility_calibration_v1.audit import load
from visibility_calibration_v1.fitting import single

ROOT=Path(__file__).resolve().parent


def main():
    verify(ROOT/'manifest.json')
    checked=[]
    for row in read(ROOT/'fits.json')['singles']:
        if row['repeat'] not in (0,10,19):
            continue
        actual=single(load(ROOT,row['index'],repeat=row['repeat']))
        assert actual=={k:v for k,v in row.items() if k not in ('index','repeat')}
        checked.append(dict(index=row['index'],repeat=row['repeat'],identical=True))
    outputs={str(p):sha(p) for p in ROOT.rglob('*') if p.suffix in ('.json','.npz')}
    save(ROOT/'audit.json',dict(passed=True,checked=checked,outputs=outputs,
        scope='each_view_first_middle_last_fit',task_success_verified=False))
    print(dict(checked=len(checked),passed=True),flush=True)


if __name__=='__main__':
    main()
