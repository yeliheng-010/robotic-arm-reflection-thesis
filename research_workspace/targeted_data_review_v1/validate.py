"""构建后独立重读导出，使用真实记录验证篡改会被拒绝。"""
from copy import deepcopy
from pathlib import Path
from common import read, save, sha
from labels import held_inputs
from verify_export import verify, verify_manifest, verify_record, read_lines

ROOT = Path('/home/yeliheng/grasp_server/targeted_data_review_v1')


def main():
    assert verify_manifest(ROOT)
    output = ROOT/'output_v1'
    raw = read_lines(output/'provenance.jsonl')
    held, old_train = held_inputs()
    checked = verify(output, raw, held=held, old_train=old_train)
    multi = read_lines(output/'multi_success.jsonl')[0]
    source = next(r for r in raw if r['input_hash'] == multi['id'])
    rejected = []
    for kind in ('drop_successful_action', 'tamper_prompt', 'change_timing', 'change_outcome'):
        row = deepcopy(multi)
        if kind == 'drop_successful_action':
            row['accepted_action_ids'].pop()
        elif kind == 'tamper_prompt':
            row['messages'][0]['content'] += ' forged'
        elif kind == 'change_timing':
            row['success_timing'] = 'forged'
        else:
            row['tested_outcomes'][0]['terminal_success'] = not row['tested_outcomes'][0]['terminal_success']
        try:
            verify_record(row, source)
        except AssertionError:
            rejected.append(kind)
        else:
            raise AssertionError('Tampered export accepted: '+kind)
    assert verify_manifest(ROOT)
    save(ROOT/'independent_verification.json', dict(passed=True, complete=True,
        manifest_sha256=sha(ROOT/'manifest.json'), exported=checked,
        real_record_tamper_rejections=rejected, training_started=False, test_used=False))
    print(dict(passed=True, inputs=checked['inputs'], tamper_rejections=len(rejected)))


if __name__ == '__main__':
    main()
