"""原视角修复批次全部五例逐一配对，不按成败择样。"""
from copy import deepcopy
from ta_common import ROOT, PILOT, SOURCE, SEEDS, read, save, sha, verify
from ta_protocol import candidate


def register(original, identities):
    seed = original['item']['seed']
    audit_path = SOURCE/'audits'/(str(seed)+'.json')
    assert verify(audit_path)['passed']
    folder = SOURCE/'cases'/str(seed)
    step = read(folder/'first/step.json')
    assert step['state'] == original['state'] and step['strategy'] == original['strategy']
    assert step['index'] == 1 and sha(step['result_path']) == step['result_sha256']
    qualification = SOURCE/'qualification'/str(seed)/'result.json'
    assert read(qualification)['qualified']
    reference = dict(case=deepcopy(original), step=str(folder/'first/step.json'),
        audit=str(audit_path), qualification=str(qualification), old_success=step['success'])
    paths = [audit_path, folder/'result.json', folder/'first/step.json', step['result_path'], qualification]
    identities.update({str(p): sha(p) for p in paths})
    return candidate(original), reference


def main():
    assert not PILOT.exists(), 'Do not repeat registered candidate runs'
    source = verify(SOURCE/'manifest.json')
    result = read(SOURCE/'result.json')
    assert result['complete'] and result['counts']['audited_pairs'] == len(SEEDS)
    assert source['seeds'] == list(SEEDS)
    identities = dict(source['identities'])
    identities.update({str(p): sha(p) for p in [SOURCE/'manifest.json', SOURCE/'result.json']})
    pairs = [register(case, identities) for case in source['cases']]
    cases, references = [p[0] for p in pairs], {str(p[0]['item']['seed']): p[1] for p in pairs}
    files = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')]
    identities.update({str(p): sha(p) for p in files})
    save(PILOT/'manifest.json', dict(cases=cases, references=references, identities=identities,
        seeds=list(SEEDS), unique_treatment='strategy_original_to_observed_top',
        max_new_attempts=5, attempts_per_case=1, max_model_calls=0, training_updates=0,
        scope='used_train_layout_capability_ablation', eligible_for_training=False))
    for seed in SEEDS:
        ref = references[str(seed)]
        qualification = deepcopy(read(ref['qualification']))
        qualification.update(manifest_sha256=sha(PILOT/'manifest.json'),
            reused_scene_qualification=True, source_path=ref['qualification'],
            source_sha256=sha(ref['qualification']),
            limitation='Original scene eligibility reused; top strategy checked by actual execution planner')
        save(PILOT/'qualification'/str(seed)/'result.json', qualification)
    print(dict(registered=len(cases), manifest_sha256=sha(PILOT/'manifest.json')), flush=True)


if __name__ == '__main__':
    main()
