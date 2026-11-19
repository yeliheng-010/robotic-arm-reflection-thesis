import numpy as np
from held_observation_v1.geometry import sample,fit,consistency
from visibility_calibration_v1.policy import NOISE_REPEATS,select_pairs


def single(cloud):
    try:
        return dict(fit=fit(sample(cloud)),failure=None)
    except (ValueError,AssertionError) as error:
        return dict(fit=None,failure=str(error))


def pair(one,two,*,fits):
    if any(row['fit'] is None for row in fits):
        return dict(fit=None,quality_passed=False,failure='single_fit_unavailable')
    try:
        combined=fit(sample(np.vstack((sample(one),sample(two)))))
        quality=consistency([combined,*[row['fit'] for row in fits]])
        return dict(fit=combined,quality_passed=quality['passed'],quality=quality,failure=None)
    except (ValueError,AssertionError) as error:
        return dict(fit=None,quality_passed=False,failure=str(error))


def run(rows,clouds):
    singles=[]
    indexed={}
    for row in rows:
        if row['index'] not in clouds:
            continue
        for repeat,cloud in enumerate(clouds[row['index']]):
            value=dict(index=row['index'],repeat=repeat,**single(cloud))
            singles.append(value)
            indexed[row['index'],repeat]=value
    selected=select_pairs([r for r in rows if r['index'] in clouds])
    pairs=[]
    for a,b in selected:
        for repeat in range(NOISE_REPEATS):
            value=pair(clouds[a][repeat],clouds[b][repeat],fits=[indexed[a,repeat],indexed[b,repeat]])
            pairs.append(dict(indices=[a,b],repeat=repeat,**value))
    return dict(singles=singles,pairs=pairs,selected_pairs=selected,
                physical_success=None,training_eligible=False)
