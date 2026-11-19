"""将助理逐条复核意见绑定到轨迹，并验证覆盖、分母和数据隔离。"""
from collections import Counter
import json
from pathlib import Path
from screening import fingerprint

ROOT = Path('/home/yeliheng/grasp_server/refinement_review_v1')


def annotate_candidates(candidates, annotations):
    flags = annotations['candidate_flags']
    assert set(flags) <= {c['id'] for c in candidates}
    for row in candidates:
        row['reviewer'] = annotations['reviewer']
        row['review_notes'] = flags.get(row['id'], [])
        row['rationale_causally_validated'] = False
        missing = any(v['measurement']=='missing' for v in row['residual_checks'].values())
        row['candidate_status'] = 'separate_exploration_candidate' if missing else 'physical_action_candidate_only'
        row['rationale_status'] = ('flagged_do_not_use_raw' if row['review_notes'] else
                                   'no_obvious_parameter_error_found_not_causal_ground_truth')
        assert not row['training_approved']


def failure_index(analysis, annotations):
    rows = analysis['failures']
    assert {str(r['case']) for r in rows} == set(annotations['failure_conditions'])
    for row in rows:
        row.update(annotations['failure_conditions'][str(row['case'])])
    lines = ['# 17 次失败逐条索引', '', '编号为 case_方法_重复，attempt 从 1 起。所有归因均为助理证据复核，不是人工专家真值。',
             '', '|运行|错误链|分类|证据说明|', '|---|---|---|---|']
    for row in rows:
        lines.append(f"|{row['id']}|{' → '.join(row['error_chain'])}|{row['category']}|{row['finding']} {row['confidence']}|")
    (ROOT/'FAILURE_INDEX.md').write_text('\n'.join(lines)+'\n')
    return rows


def candidate_index(candidates):
    lines = ['# 成功转移候选复核', '', '以下不是训练文件：所有条目 training_approved=false。模型与专家分开，保留原始解释及其缺陷。',
             '', '|候选|来源|后继物理成功|复核状态|标记|', '|---|---|---|---|---|']
    for row in sorted(candidates, key=lambda r:r['id']):
        notes = '；'.join(row['review_notes']) or '未发现明显参数语义错误；因果解释未经验证'
        lines.append(f"|{row['id']}|{row['source']}|{row['next_accepted']}|{row['candidate_status']}|{notes}|")
    (ROOT/'CANDIDATE_INDEX.md').write_text('\n'.join(lines)+'\n')


def main():
    analysis = json.loads((ROOT/'analysis.json').read_text())
    candidates = json.loads((ROOT/'candidates.json').read_text())
    annotations = json.loads((ROOT/'annotations.json').read_text())
    rows = failure_index(analysis, annotations)
    annotate_candidates(candidates, annotations)
    candidate_index(candidates)
    for source in ('llm', 'rule_expert'):
        with (ROOT/(source+'_reviewed_candidates.jsonl')).open('w') as stream:
            for row in candidates:
                if row['source'] == source:
                    stream.write(json.dumps(row, ensure_ascii=False)+'\n')
    result = dict(failure_runs=len(rows), categories=dict(Counter(r['category'] for r in rows)),
                  candidate_count=len(candidates), flagged_raw_rationales=sum(bool(r['review_notes']) for r in candidates),
                  flagged_new_rationales=sum(bool(r['review_notes']) and r['arm']=='flash_new' for r in candidates),
                  approved_training_samples=0, test_used=False,
                  reviewer=annotations['reviewer'], annotation_sha256=fingerprint(annotations))
    (ROOT/'review_verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
