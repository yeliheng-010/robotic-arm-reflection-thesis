from qualified_model_v1.common import ROOT, PROJECT, RUN, SEEDS, read, save, sha
from qualified_model_v1.policy import SYSTEM


def main():
    source = PROJECT/'qualified_task_v1/run'
    audit = read(source/'audit_result.json')
    assert audit['passed'] and len(audit['rows']) == 2
    cases = read(source/'manifest.json')['cases']
    entries, paths = [], [source/'audit_result.json', source/'manifest.json']
    for seed in SEEDS:
        folder = source/f'audit/{seed}'
        result = read(folder/'result.json')
        assert result['passed'] and sha(folder/'qualified.png') == result['image_sha256']
        color = cases[str(seed)]['config']['appearance']['RedBin']['color']
        request = dict(seed=seed, image=str(folder/'qualified.png'),
            image_sha256=result['image_sha256'], messages=[dict(role='system', content=SYSTEM),
                dict(role='user', content=f'任务：把紫色胶囊放进{color}箱子。请定位待抓物体和目标容器。')])
        save(RUN/f'{seed}/request.json', request)
        entries.append(dict(seed=seed, request=str(RUN/f'{seed}/request.json')))
        paths.extend([folder/'qualified.png', folder/'result.json', RUN/f'{seed}/request.json'])
    paths.extend(p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md'))
    save(RUN/'manifest.json', dict(entries=entries, identities={str(p): sha(p) for p in paths},
        max_model_calls=2, max_task_attempts=0, max_training_runs=0, camera_searches=0,
        inputs='Qualified RGB and natural language only; no simulator points, masks or failure labels',
        role='Image grounding; no grasp strategy or physical success claim'))
    print(dict(registered=2, model_calls=0), flush=True)


if __name__ == '__main__':
    main()
