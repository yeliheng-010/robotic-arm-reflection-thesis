"""在Slurm中冻结旧证据、所有项目生成依赖及新请求。"""
import os
from qualified_prompt_checkpoint_v1.protocol import ROOT, PROJECT, RUN, read, save, sha, build_request

MODULES = ('ai_visual_input_v1', 'ai_diagnosis_failure_v1', 'ai_diagnosis_v1',
           'candidate_sft_v2', 'model_grasp_intent_v1', 'qualified_feedback_v1')


def parent_identities():
    parent = PROJECT / 'qualified_closure_feedback_v1'
    identities = dict(read(parent / 'run/manifest.json')['identities'])
    identities.update(read(PROJECT / 'candidate_sft_v2/manifest.json')['identities'])
    inventory = read(parent / 'run/delivery_inventory.json')
    identities.update({str(parent / p): h for p, h in inventory['identities'].items()})
    identities[str(parent / 'run/delivery_inventory.json')] = sha(parent / 'run/delivery_inventory.json')
    old = read(parent / 'run/result.json')
    assert old['generations_started'] == 2 and old['ready_ordinal'] is None
    assert old['rows'][1]['status'] == 'repeated_rejected_action'
    assert read(PROJECT / 'qualified_execution_v1/run/attempt_claim.json')['consumed'] == 1
    return identities


def source_paths():
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md', '.json')]
    for module in MODULES:
        paths += list((PROJECT / module).glob('*.py'))
    for folder in ('ai_visual_input_v1/torchvision_overlay', 'stability_20261019/stability'):
        paths += list((PROJECT / folder).rglob('*.py'))
    paths += [PROJECT / 'candidate_sft_v2/manifest.json', PROJECT / 'candidate_sft_v2/environment.sh',
              PROJECT / 'improvement_20261019/code/training/server/qwen35_env.sh']
    model = PROJECT / 'qwen35/models/Qwen3.5-4B'
    paths += [p for p in model.iterdir() if p.is_file()]
    return sorted(set(paths))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    identities = parent_identities()
    for name, expected in identities.items():
        assert sha(name) == expected, name
    baseline = PROJECT / 'qualified_closure_feedback_v1/run/decision_2/request.json'
    request = build_request(read(baseline), read(ROOT / 'B_checkpoint.json'))
    save(RUN / 'request.json', request)
    paths = source_paths() + [RUN / 'request.json']
    identities.update({str(p): sha(p) for p in paths})
    save(RUN / 'manifest.json', dict(seed=978505, max_model_calls=1, max_planning=0,
         max_physical=0, max_training=0, max_camera_search=0, identities=identities,
         baseline_request=str(baseline), draft_sha256=sha(ROOT / 'B_checkpoint.json'),
         request_sha256=sha(RUN / 'request.json'), registration_job=os.environ['SLURM_JOB_ID'],
         prompt_changes=['append decision_checkpoint', 'budget.planning: 1 -> 0'],
         stop_after_one=True, retry_allowed=False))
    print(dict(registered=True, identities=len(identities), model_budget=1, planning=0, physical=0), flush=True)


if __name__ == '__main__':
    main()
