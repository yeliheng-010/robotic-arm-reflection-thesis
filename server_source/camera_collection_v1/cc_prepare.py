"""固定五个已经通过相机资格的训练布局；不按物理结果换种子。"""
from copy import deepcopy
from cv_entry import approved_config
from cc_common import ROOT, PARENT, PILOT, SEEDS, read, save, sha, verify
from cc_policy import adopt


def source(seed):
    batch = '000' if seed < 964100 else '009'
    base = PARENT/'recovery_collection_v1/batches'/batch/'physics'
    manifest = verify(base/'manifest.json')
    name = f'R0_{seed}_varied_noisy'
    case = next(c for c in manifest['cases'] if c['item']['id'] == name)
    audit = base/'audits'/(name+'.json')
    if verify(audit)['passed'] is not True:
        raise ValueError('Historical condition is not audit accepted')
    return case, base, audit


def selected(seed):
    suffix = 'extra/job_6310' if seed < 964100 else 'runs/job_6309'
    return PARENT/'camera_visibility_v6'/suffix/str(seed)


def prepare_case(seed, identities):
    original, base, audit = source(seed)
    identities.update(read(base/'manifest.json')['identities'])
    selection = selected(seed)
    config = approved_config(selection, original['config'])
    case = adopt(original, config)
    step_path = base/'cases'/original['item']['id']/'first/step.json'
    old = read(step_path)
    assert old['index'] == 1 and old['state'] == case['state']
    assert old['strategy'] == case['strategy'] and old['control'] == case['control']
    assert sha(old['result_path']) == old['result_sha256']
    case['camera_collection'] = dict(original=deepcopy(original), selection=str(selection),
        old_step=str(step_path), old_audit=str(audit), purpose='used_train_layout_engineering_pilot')
    case.pop('qualification', None)
    paths = [base/'manifest.json', audit, step_path, old['result_path'],
             selection/'selection.json', selection/'accepted_config.json']
    identities.update({str(p): sha(p) for p in paths})
    return case


def main():
    assert not PILOT.exists(), 'Never overwrite or repeat a registered pilot'
    camera_root = PARENT/'camera_visibility_v6'
    audits = [camera_root/'audits/job_6311/result.json', camera_root/'extra_audits/job_6312/result.json']
    for path in audits:
        assert verify(path)['passed']
    identities = {str(p): sha(p) for p in audits}
    cases = [prepare_case(seed, identities) for seed in SEEDS]
    files = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')]
    files += [p for p in camera_root.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')]
    identities.update({str(p): sha(p) for p in files})
    save(PILOT/'manifest.json', dict(cases=cases, identities=identities, seeds=list(SEEDS),
        registered_camera_layouts=9, camera_accepted=5, camera_rejected=4,
        max_new_attempts=5, attempts_per_case=1, max_model_calls=0, training_updates=0,
        final_test_used=False, eligible_for_training=False))
    print(dict(registered=5, manifest_sha256=sha(PILOT/'manifest.json')), flush=True)


if __name__ == '__main__':
    main()
