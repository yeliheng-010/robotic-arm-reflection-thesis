import os
from pathlib import Path
from prompts import messages
from mm_common import ROOT, SOURCE, CASE, read, save, sha, verify


def main():
    assert os.environ.get('SLURM_JOB_ID')
    parent = verify()
    assert not list(ROOT.glob('*_started.json')), 'Do not silently replace input after model preparation'
    bundle = read(ROOT/'input.json')
    before = SOURCE/'cases'/CASE/'attempt_1/execution/attempt_1/before.png'
    after = Path(bundle['visual']['original_rgb'])
    assert sha(before) == parent['identities'][str(before)]
    assert sha(after) == parent['identities'][str(after)]
    request = bundle['request']
    row = next(r for r in request['evidence'] if r['field']=='attached_rgb_images')
    row['value'] = ['before_attempt_full_camera_frame', 'after_attempt_paused_full_camera_frame']
    row['source'] = 'two_saved_rgb_frames_from_the_same_completed_attempt'
    request['sensing_status']['rgb'] = 'attached_before_and_after_in_order'
    request['version'] = 'visual-temporal-input-smoke-v1'
    target = ROOT/'temporal_v2'
    target.mkdir(exist_ok=False)
    save(target/'input.json', dict(request=request, visual=dict(paths=[str(before), str(after)],
        sha256=[sha(before), sha(after)], order=['before', 'after']),
        direct_messages=messages(request, mode='direct'), diagnostic_messages=messages(request, mode='diagnostic')))
    identities = dict(parent['identities'])
    for path in [ROOT/'manifest.json', target/'input.json', ROOT/'TEMPORAL_INPUT.md',
                 ROOT/'mm_prepare_temporal.py', ROOT/'mm_temporal_run.py', ROOT/'temporal_prepare.sbatch', ROOT/'temporal_model.sbatch']:
        identities[str(path)] = sha(path)
    save(target/'manifest.json', dict(identities=identities, model_calls=2, old_input_model_calls=0,
        physical_attempts=0, training_ready=False, source_condition=CASE, source_attempt=1))
    print(dict(images=2, frozen=sha(target/'manifest.json')), flush=True)


if __name__ == '__main__':
    main()
