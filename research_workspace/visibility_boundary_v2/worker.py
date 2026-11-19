from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from surface_grasp_v1.common import read,save,sha
from surface_physical_v1.common import verify
from sd_inventory import root_boxes
from cv_policy import REQUIRED
from coverage_repair_v1.proposals import changed
import visibility_calibration_v1.capture as sensing
from visibility_calibration_v1.fitting import single
from visibility_calibration_v1.analysis import annotate

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
PRIOR=PROJECT/'visibility_calibration_v1'
SOURCE=PROJECT/'held_observation_v3/trial/cases/964347/first/checkpoints/before_release'
REPEATS=20
SEED_PREFIX=976513
ELEVATION_OFFSETS=range(6)


def prepare():
    old=verify(PRIOR/'manifest.json')
    assert read(PRIOR/'audit.json')['passed']
    identities=dict(old['identities'],**read(PRIOR/'completed.json')['outputs'])
    paths=[p for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sbatch')]
    paths += [PRIOR/'audit.json',PRIOR/'analysis.json',PRIOR/'completed.json',
        PROJECT/'visibility_boundary_v1/analysis.json',PROJECT/'visibility_boundary_v1/audit.json']
    identities.update({str(p):sha(p) for p in paths})
    save(ROOT/'manifest.json',dict(identities=identities,max_views=6,noise_repeats=REPEATS,
        task_motion_attempts=0,model_calls=0,training_runs=0,independent_layouts=1))


def capture():
    previous=read(PRIOR/'phases/before_release/views.json')
    anchor=next(r['camera'] for r in previous if r['index']==15)
    rows,clouds=[],{}
    with sensing.restored(SOURCE) as (env,renderer,snapshot):
        all_boxes=root_boxes(env.mj_model,env.mj_data)
        boxes={name:all_boxes[name] for name in REQUIRED}
        bounds=np.asarray(list(boxes.values()))
        center=(bounds[:,0].min(axis=0)+bounds[:,1].max(axis=0))/2
        for index,offset in enumerate(ELEVATION_OFFSETS):
            camera=changed(anchor,np.array([0.,-offset,0.,0.,0.,0.]),center)
            assert camera is not None
            row,data=sensing.view(env,renderer,camera=camera,boxes=boxes,snapshot=snapshot,
                phase_id=2,index=index,folder=ROOT/f'view_{index}')
            rows.append(row)
            if data is not None:
                clouds[index]=data
    save(ROOT/'views.json',rows)
    return rows,clouds


def main():
    prepare()
    with patch.object(sensing,'NOISE_REPEATS',REPEATS),patch.object(sensing,'SEED_PREFIX',SEED_PREFIX):
        rows,clouds=capture()
    singles=[dict(index=index,repeat=repeat,**single(cloud))
             for index,values in clouds.items() for repeat,cloud in enumerate(values)]
    fits=dict(singles=singles,pairs=[])
    save(ROOT/'fits.json',fits)
    truth=read(PRIOR/'phases/before_release/private_truth.json')
    errors=annotate(fits,rows,truth)
    save(ROOT/'private_errors.json',errors)
    table=[]
    for row in rows:
        group=[r for r in errors['singles'] if r['index']==row['index']]
        distances=[r['center_error_m'] for r in group if r['center_error_m'] is not None]
        table.append(dict(index=row['index'],visibility=row['source_fraction'],
            elevation_deg=row['camera']['elevation_deg'],calibrated=row['calibration_passed'],
            count=len(group),accurate=sum(r['accurate'] for r in group),
            quality_accepted=sum(r['quality_passed'] for r in group),
            median_center_error_m=float(np.median(distances)) if distances else None,
            max_center_error_m=max(distances) if distances else None))
    verify(ROOT/'manifest.json')
    save(ROOT/'analysis.json',dict(rows=table,inputs_unchanged=True,independent_layouts=1,
        task_motion_attempts=0,high_success_threshold=None,threshold_deployed=False))
    print(table,flush=True)


if __name__=='__main__':
    main()
