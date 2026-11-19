"""只读解释已消费候选；反事实不代表新渲染、标定或任务成功。"""
from collections import Counter
import json
from pose_fresh_review_v1.verify import ROOT, SOURCE, read

THRESHOLDS = (.85, .8, .75, .7, .6)


def candidate(row):
    rejected = row['gate']['rejected']
    return dict(index=row['index'], rejected=rejected,
        details={name: dict(row['measurements'][name], **row['gate']['objects'][name]) for name in rejected},
        calibration=row.get('calibration'))


def analyze(seed, result):
    selection = read(SOURCE / seed / 'selection.json')
    attempts = selection['attempts']
    measured = [r for r in attempts if 'gate' in r]
    names = Counter(n for r in measured for n in r['gate']['rejected'])
    reasons = Counter(reason for r in measured for o in r['gate']['objects'].values() for reason in o['reasons'])
    best = min(measured, key=lambda r: (len(r['gate']['rejected']),
        -min(o['visible_fraction'] for o in r['gate']['objects'].values()), r['index'])) if measured else None
    counterfactual = {str(t): sum(all(o['visible_fraction'] >= t
        and not (set(o['reasons']) - {'visible_fraction'}) for o in r['gate']['objects'].values())
        for r in measured) for t in THRESHOLDS}
    assert selection['accepted'] == result['qualified']
    assert len(attempts) <= 256 and (result['qualified'] or len(attempts) == 256)
    assert [r['index'] for r in attempts] == list(range(len(attempts)))
    return dict(seed=seed, qualified=result['qualified'], candidates=len(attempts),
        framed=len(measured), framing_rejected=len(attempts)-len(measured),
        object_rejections=dict(names), reason_counts=dict(reasons),
        gate_only_counterfactual_no_new_calibration=counterfactual,
        best_by_fewest_rejected_then_minimum_visibility=candidate(best) if best else None,
        calibration_failures=[candidate(r) for r in measured if r['gate']['passed'] and not r['accepted']])


def main():
    audit = read(SOURCE / 'audit.json')
    rows = [analyze(seed, result) for seed, result in audit['layouts'].items()]
    rejected = [r for r in rows if not r['qualified']]
    totals = {key: sum(r[key] for r in rows) for key in ('candidates', 'framed', 'framing_rejected')}
    counterfactual = {str(t): sum(r['gate_only_counterfactual_no_new_calibration'][str(t)] > 0 for r in rejected)
                      for t in THRESHOLDS}
    result = dict(layouts=rows, totals=totals, failed_layouts=len(rejected),
        failed_layouts_with_gate_only_candidate=counterfactual,
        no_new_rendering=True, no_new_task_attempts=True, thresholds_unchanged=True,
        caution='Post-hoc diagnostic on consumed views; missing depth checks stay unknown; not control or training inputs')
    (ROOT / 'diagnosis.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(dict(totals=totals, failed_layouts=len(rejected), gate_only_counterfactual=counterfactual))


if __name__ == '__main__':
    main()
