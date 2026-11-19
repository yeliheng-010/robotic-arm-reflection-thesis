from pathlib import Path
from reflection.__main__ import bootstrap
bootstrap()
from surface_grasp_v1.common import read,save,sha
from surface_physical_v1.common import verify
from visibility_calibration_v1.capture import capture
from visibility_calibration_v1.fitting import run as fit
from visibility_calibration_v1.analysis import run as analyze

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
SOURCES=dict(preflight=PROJECT/'held_observation_v2/trial/preflight/checkpoints/preflight',
    after_lift=PROJECT/'held_observation_v3/trial/cases/964347/first/checkpoints/after_lift',
    before_release=PROJECT/'held_observation_v3/trial/cases/964347/first/checkpoints/before_release')


def prepare():
    old=verify(PROJECT/'held_observation_review_v2/manifest.json')
    identities=dict(old['identities'],**old['source_identities'])
    verify(PROJECT/'held_observation_v3/trial/execution_manifest.json')
    paths=[p for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sbatch')]
    paths+=[p for source in SOURCES.values() for p in source.rglob('*') if p.is_file()]
    identities.update({str(p):sha(p) for p in paths})
    save(ROOT/'manifest.json',dict(identities=identities,task_motion_attempts=0,model_calls=0,
        training_runs=0,max_cameras=96,max_pairs_per_phase=24,noise_repeats=3,
        private_diagnostic=True,independent_layouts=1))


def main():
    prepare()
    for phase_id,(name,source) in enumerate(SOURCES.items()):
        folder=ROOT/'phases'/name
        rows,clouds=capture(source,folder,phase_id=phase_id)
        print(dict(phase=name,cameras=len(rows),calibrated=len(clouds)),flush=True)
        results=fit(rows,clouds)
        save(folder/'fits.json',results)
        print(dict(phase=name,singles=len(results['singles']),pairs=len(results['pairs'])),flush=True)
    result=analyze(ROOT,SOURCES)
    verify(ROOT/'manifest.json')
    outputs={str(p):sha(p) for p in (ROOT/'phases').rglob('*') if p.is_file()}
    save(ROOT/'completed.json',dict(inputs_unchanged=True,outputs=outputs,
        task_motion_attempts=0,high_success_threshold=result['high_success_threshold']))
    print({name:row['all_pairs'] for name,row in result['phases'].items()},flush=True)


if __name__=='__main__':
    main()
