import numpy as np
from surface_grasp_v1.common import read,save
from visibility_calibration_v1.policy import THRESHOLDS,gate_at

CENTER_LIMIT_M=.010
AXIS_LIMIT_DEG=12.


def accuracy(fitted,truth):
    if fitted is None:
        return dict(accurate=False,center_error_m=None,axis_error_deg=None)
    center=float(np.linalg.norm(np.asarray(fitted['center'])-truth['center']))
    angle=float(np.rad2deg(np.arccos(np.clip(abs(np.dot(fitted['axis'],truth['axis'])),0.,1.))))
    return dict(accurate=center<=CENTER_LIMIT_M and angle<=AXIS_LIMIT_DEG,
                center_error_m=center,axis_error_deg=angle)


def single_quality(fitted):
    return (fitted is not None and fitted['converged'] and fitted['p95_m']<=.006
            and fitted['condition']<1e4 and fitted['half_length']>=fitted['radius'])


def annotate(fits,views,truth):
    indexed={row['index']:row for row in views}
    result={}
    for kind in ('singles','pairs'):
        rows=[]
        for row in fits[kind]:
            indices=row.get('indices',[row.get('index')])
            quality=row['quality_passed'] if kind=='pairs' else single_quality(row['fit'])
            rows.append(dict(row,**accuracy(row['fit'],truth),quality_passed=bool(quality),
                visibility=min(indexed[i]['source_fraction'] for i in indices),
                full_frame_other_gates=all(gate_at(indexed[i]['report'],0.) for i in indices)))
        result[kind]=rows
    return result


def summary(rows):
    accepted=[r for r in rows if r['quality_passed']]
    errors=[r['center_error_m'] for r in rows if r['center_error_m'] is not None]
    accurate=sum(r['accurate'] for r in rows)
    trusted=sum(r['accurate'] for r in accepted)
    return dict(observations=len(rows),accurate=accurate,quality_accepted=len(accepted),
        quality_accepted_accurate=trusted,false_accepts=len(accepted)-trusted,
        accuracy=accurate/len(rows) if rows else None,
        accepted_accuracy=trusted/len(accepted) if accepted else None,
        median_center_error_m=float(np.median(errors)) if errors else None,
        p95_center_error_m=float(np.percentile(errors,95)) if errors else None,
        minimum_center_error_m=min(errors) if errors else None)


def phase(folder):
    views=read(folder/'views.json')
    errors=annotate(read(folder/'fits.json'),views,read(folder/'private_truth.json'))
    save(folder/'private_errors.json',errors)
    grids=[]
    for threshold in THRESHOLDS:
        frames=[r['index'] for r in views if gate_at(r['report'],threshold) and r['calibration_passed']]
        grid=dict(threshold=threshold,full_frame_qualified=len(frames),indices=frames)
        for kind in ('singles','pairs'):
            grid[kind]=summary([r for r in errors[kind] if r['visibility']>=threshold])
        grids.append(grid)
    return dict(cameras=len(views),calibrated=sum(r['calibration_passed'] for r in views),
        target_visibility_max=max(r['source_fraction'] for r in views),
        all_singles=summary(errors['singles']),all_pairs=summary(errors['pairs']),thresholds=grids)


def run(root,phases):
    report={name:phase(root/'phases'/name) for name in phases}
    result=dict(phases=report,independent_layouts=1,noise_repeats=3,high_success_threshold=None,
        physical_task_success_rate=None,task_motion_attempts=0,model_calls=0,training_runs=0,
        threshold_deployed=False,conclusion='Exploratory pose calibration; no independent task validation')
    save(root/'analysis.json',result)
    return result
