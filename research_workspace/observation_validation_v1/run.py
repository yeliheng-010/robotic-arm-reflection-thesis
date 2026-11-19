"""四卡分片，已完成冒烟只读复核，部分输出禁止重跑。"""
import argparse
import os
import subprocess
from pilot import ROOT, SMOKE_SEEDS, SHARDS, verify, read, save, sha
from audit import audit_scene


def run(phase, shard):
    manifest = verify()
    if phase == 'batch':
        gate = read(ROOT/'gate_smoke.json')
        assert gate['passed'] and gate['manifest_sha256'] == sha(ROOT/'manifest.json')
    order = [(i, s) for i, s in enumerate(manifest['scenes']) if phase == 'batch' or s['seed'] in SMOKE_SEEDS]
    directory = ROOT/'stages'/phase/f'shard_{shard}'
    directory.mkdir(parents=True, exist_ok=False)
    (ROOT/'logs').mkdir(exist_ok=True)
    order = order[shard::SHARDS]
    status = dict(status='running', expected=len(order), completed=0, rows=[], job=os.environ['SLURM_JOB_ID'])
    save(directory/'progress.json', status)
    try:
        for index, scene in order:
            task = ROOT/'tasks'/scene['id']
            if not (task/'summary.json').exists():
                assert not task.exists(), 'Partial task requires diagnosis'
                with (ROOT/'logs'/f"{scene['id']}.log").open('x') as stream:
                    subprocess.run([str(ROOT.parent/'env_sim/bin/python'), str(ROOT/'worker.py'), str(index)],
                                   check=True, timeout=1800, stdout=stream, stderr=subprocess.STDOUT)
            checked = audit_scene(read(task/'result.json'))
            assert checked == read(task/'summary.json')
            status['rows'].append(checked)
            status['completed'] += 1
            save(directory/'progress.json', status)
        status['status'] = 'completed'
    except BaseException as error:
        status.update(status='failed', error=repr(error))
        raise
    finally:
        save(directory/'progress.json', status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['smoke', 'batch'])
    parser.add_argument('--shard', type=int, required=True, choices=range(SHARDS))
    args = parser.parse_args()
    run(args.phase, args.shard)
