"""全分母审计、真实记录篡改检测与独立监督候选导出。"""
import argparse
import json
from copy import deepcopy
from audit import audit_scene, audit_trace
from labels import records, summarize
from pilot_common import ROOT, SEEDS, SHARDS, verify, read, save, sha


def tamper(values):
    eligible = next(v for v in values if v['eligible'] and v['nodes'])
    trace = read(eligible['trajectories'][0])
    scene = eligible['scene']
    q = read(ROOT/'qualification'/scene['id']/'result.json')
    reference = read(q['steps'][0]['result_path'])['records'][0]
    rejected = []
    for kind in ('physical_hash', 'visible_feedback', 'selected_state', 'terminal_success'):
        changed = deepcopy(trace)
        if kind == 'physical_hash':
            changed['attempts'][0]['result_sha256'] = '0'*64
        elif kind == 'visible_feedback':
            changed['attempts'][0]['feedback']['error_type'] = 'forged'
        elif kind == 'selected_state':
            changed['decisions'][0]['selected']['state']['profile'] = 'forged'
        else:
            changed['success'] = not changed['success']
        try:
            audit_trace(changed, reference)
        except (AssertionError, ValueError, KeyError):
            rejected.append(kind)
        else:
            raise AssertionError('Tamper accepted: '+kind)
    return dict(passed=True, rejected=rejected, total_rejections=len(rejected))


def main(phase):
    manifest = verify()
    scenes = [s for s in manifest['scenes'] if phase == 'final' or s['seed'] == SEEDS[0]]
    stage = 'batch' if phase == 'final' else 'smoke'
    for shard in range(SHARDS):
        assert read(ROOT/'stages'/stage/f'shard_{shard}/progress.json')['status'] == 'completed'
    values, checked, nodes = [], [], []
    for scene in scenes:
        value = read(ROOT/'tasks'/scene['id']/'result.json')
        assert value['scene'] == scene
        row = audit_scene(value)
        assert row == read(ROOT/'tasks'/scene['id']/'summary.json')
        values.append(value)
        checked.append(row)
        nodes.extend(records(value))
    checks = tamper(values)
    summary = dict(passed=True, complete=True, expected=len(scenes), accounted=len(checked),
        eligible=sum(r['eligible'] for r in checked), skipped=sum(not r['eligible'] for r in checked),
        baseline_successes=sum(r['baseline_success'] is True for r in checked),
        physical_executions=sum(r['physical_executions'] for r in checked),
        physical_budget=len(scenes)*manifest['max_physical_per_scene'],
        trajectories=sum(r['trajectories'] for r in checked), labels=summarize(nodes),
        tamper=checks, model_calls=0, training_approved=False, test_used=False,
        manifest_sha256=sha(ROOT/'manifest.json'), rows=checked)
    assert summary['physical_executions'] <= summary['physical_budget']
    save(ROOT/f'{phase}_verification.json', summary)
    save(ROOT/f'{phase}_node_outcomes.json', nodes)
    if phase == 'smoke':
        save(ROOT/'gate_smoke.json', dict(passed=True, manifest_sha256=summary['manifest_sha256']))
    else:
        text = ['# 定向试采结果', '', f"处理{summary['accounted']}/{summary['expected']}个条件，"
                f"合格{summary['eligible']}，跳过{summary['skipped']}。",
                f"独立物理执行{summary['physical_executions']}/{summary['physical_budget']}次，模型调用0。",
                '', '监督候选统计：', '```json', json.dumps(summary['labels'], ensure_ascii=False, indent=2),
                '```', '', '规则分支搜索数据，非模型生成数据。成功动作集合仅覆盖已试分支，后续策略固定为规则。',
                '同输入多解、矛盾与开发重合保留并标记；未自动导出SFT或启动训练。']
        (ROOT/'REPORT.md').write_text('\n'.join(text)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k != 'rows'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['smoke', 'final'])
    args = parser.parse_args()
    try:
        main(args.phase)
    except BaseException as error:
        save(ROOT/f'{args.phase}_audit_failure.json', dict(passed=False, error=repr(error)))
        raise
