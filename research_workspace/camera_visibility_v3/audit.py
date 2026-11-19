"""独立重建合格场景；不执行抓取、不把资格成功当任务成功。"""
import os
from pathlib import Path
from sd_common import read, save, sha
from sd_inventory import root_boxes
from cv_entry import approved_config
from cv_select import scene, evaluate, image, PROPOSAL_BUDGET
from cv_policy import REQUIRED, frame_gate
from run import CASES

ROOT = Path(__file__).resolve().parent


def audit_case(folder, original, *, output):
    report = read(folder/'selection.json')
    for row in report['attempts']:
        if 'measurements' in row:
            assert frame_gate(row['measurements']) == row['gate']
    if not report['accepted']:
        assert not (folder/'accepted_config.json').exists()
        assert len(report['attempts']) == PROPOSAL_BUDGET
        return dict(seed=report['seed'], accepted=False, rejection_preserved=True)
    config = approved_config(folder, original)
    with scene(config) as (env, renderer):
        boxes = root_boxes(env.mj_model, env.mj_data)
        actual = evaluate(env, renderer, config['camera'], boxes={n: boxes[n] for n in REQUIRED})
        assert actual['accepted']
        assert actual['measurements'] == report['attempts'][-1]['measurements']
        digest = image(env, output/(str(report['seed'])+'.png'))
        assert digest == sha(folder/'after.png')
    return dict(seed=report['seed'], accepted=True, independent_render=True,
                identical_rgb=True, identical_metrics=True)


def main():
    job = os.environ['SLURM_JOB_ID']
    run = os.environ['CV_RUN_JOB']
    assert run.isdecimal()
    output = ROOT/'audits'/('job_'+job)
    output.mkdir(parents=True, exist_ok=False)
    source = ROOT/'runs'/('job_'+run)
    summary = read(source/'summary.json')
    assert all(sha(p) == h for p, h in summary['identities'].items())
    rows = []
    for batch, seed in CASES:
        path = ROOT.parent/'recovery_collection_v1/batches'/batch/'physics/manifest.json'
        case = next(c for c in read(path)['cases'] if c['item']['id'] == f'R0_{seed}_varied_noisy')
        rows.append(audit_case(source/str(seed), case['config'], output=output))
    paths = [p for p in source.rglob('*') if p.is_file()]
    save(output/'result.json', dict(passed=True, source_job=run, rows=rows,
        identities={str(p): sha(p) for p in paths}, physical_attempts=0, model_calls=0))
    print(rows, flush=True)


if __name__ == '__main__':
    main()
