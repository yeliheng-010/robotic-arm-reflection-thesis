"""登记固定动作静态预算；冻结已审计模型输出及旧输入。"""
import json
import os
from qualified_checkpoint_preflight_v1.protocol import ROOT, PROJECT, RUN, SOURCE, CAPS, read, save, sha, source_action


def main():
    assert os.environ.get('SLURM_JOB_ID')
    action = source_action()
    identities = dict(read(SOURCE / 'manifest.json')['identities'])
    inventory = read(SOURCE / 'delivery_inventory.json')
    assert inventory['passed']
    identities.update({str(SOURCE.parent / name): digest for name, digest in inventory['identities'].items()})
    for name, expected in identities.items():
        assert sha(name) == expected, name
    request = read(SOURCE / 'request.json')
    geometry = read(PROJECT / 'qualified_path_v1/run/goals/978505/geometry.json')
    from qualified_joint_feedback_v1.policy import GEOMETRY_KEYS, compact
    body = json.loads(request['messages'][1]['content'])
    assert body['observed_placement'] == {key: compact(geometry[key]) for key in GEOMETRY_KEYS}
    save(RUN / 'input.json', dict(seed=978505, action=action, history=body['history'], geometry=geometry,
         response_sha256=sha(SOURCE / 'response.json'), source_request_sha256=sha(SOURCE / 'request.json')))
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sbatch', '.sh')]
    paths += [p for p in SOURCE.rglob('*') if p.is_file()]
    paths += [RUN / 'input.json']
    identities.update({str(path): sha(path) for path in paths})
    save(RUN / 'manifest.json', dict(**CAPS, identities=identities, seed=978505,
         input_sha256=sha(RUN / 'input.json'), original_model_request_unchanged=True,
         registration_job=os.environ['SLURM_JOB_ID'], physical_registered=False))
    print(dict(registered=True, frozen_identities=len(identities), action=action, **CAPS), flush=True)


if __name__ == '__main__':
    main()
