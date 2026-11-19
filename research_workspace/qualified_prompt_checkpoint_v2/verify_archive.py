"""本地核验两版本预算、来源、输入张量与新动作；不运行模型/仿真。"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
EVIDENCE, REMOTE = ROOT / 'evidence', ROOT / 'evidence/remote'
RUN = REMOTE / 'run'
PRIOR = ROOT.parent / 'qualified_prompt_checkpoint_v1/evidence/remote'
OUTPUT = EVIDENCE / 'FINAL_VERIFICATION.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files():
    rows = read(EVIDENCE / 'DELIVERY.json')['files']
    seen, sources = set(), 0
    for row in rows:
        path = (REMOTE / row['path']).resolve()
        assert path.is_relative_to(REMOTE.resolve())
        assert row['path'] not in seen and row['sha256'] == sha(path)
        seen.add(row['path'])
        if len(Path(row['path']).parts) == 1 and path.suffix in ('.py', '.md', '.json', '.sh', '.sbatch'):
            assert row['sha256'] == sha(ROOT / row['path'])
            sources += 1
    inventory = read(RUN / 'delivery_inventory.json')
    for name, expected in inventory['identities'].items():
        assert expected == sha(REMOTE / name), name
    manifest = read(RUN / 'manifest.json')
    previous_rows = read(PRIOR.parent / 'DELIVERY.json')['files']
    for row in previous_rows:
        key = '/home/yeliheng/grasp_server/qualified_prompt_checkpoint_v1/' + row['path']
        assert manifest['identities'][key] == row['sha256'] == sha(PRIOR / row['path'])
    claim = ROOT.parent / 'qualified_execution_v1/evidence/remote/run/attempt_claim.json'
    assert read(claim)['consumed'] == 1 and inventory['original_claim_sha256'] == sha(claim)
    return dict(downloaded=len(rows), byte_identical_sources=sources,
                prior_downloaded_verified=len(previous_rows), frozen_identities=len(manifest['identities']))


def tensors():
    encoding = read(RUN / 'encoding.json')
    assert encoding == read(PRIOR / 'run/encoding.json')
    assert encoding['npz_sha256'] == sha(RUN / 'input_tensors.npz')
    with zipfile.ZipFile(RUN / 'input_tensors.npz') as archive:
        assert set(archive.namelist()) == {key + '.npy' for key in encoding['tensors']}
        for name in archive.namelist():
            blob = archive.read(name)
            assert blob[:8] == b'\x93NUMPY\x01\x00'
            length = struct.unpack('<H', blob[8:10])[0]
            header = ast.literal_eval(blob[10:10 + length].decode('latin1'))
            data, key = blob[10 + length:], name[:-4]
            assert header['fortran_order'] is False
            assert list(header['shape']) == encoding['tensors'][key]['shape']
            assert hashlib.sha256(data).hexdigest() == encoding['tensors'][key]['sha256']
            if key in ('input_ids', 'attention_mask'):
                assert header['descr'] == '<i8'
                assert encoding[key] == [list(struct.unpack('<' + str(len(data) // 8) + 'q', data))]
    assert read(RUN / 'request.json')['messages'][1]['content'] in read(RUN / 'templates.json')['decoded_input']
    assert read(RUN / 'templates.json') == read(PRIOR / 'run/templates.json')
    return dict(input_tokens=encoding['encoding']['input_tokens'], keys=sorted(encoding['tensors']),
                actual_input_matches_failed_preparation=True)


def outcome():
    manifest = read(RUN / 'manifest.json')
    assert manifest['max_model_calls'] == manifest['total_authorized_actual_generations'] == 1
    assert sha(RUN / 'request.json') == sha(PRIOR / 'run/request.json')
    prior = read(PRIOR / 'run/failure_audit.json')
    assert prior['passed'] and prior['model_calls'] == prior['generations_started'] == 0
    assert all(not (PRIOR / 'run' / name).exists() for name in prior['absent_files'])
    for folder in (RUN, PRIOR / 'run'):
        assert read(folder / 'model_claim.json') == dict(ordinal=1, consumed=1, request_sha256=sha(folder / 'request.json'))
    response, result = read(RUN / 'response.json'), read(RUN / 'result.json')
    action = json.loads(response['text'])['action']
    history = json.loads(read(RUN / 'request.json')['messages'][1]['content'])['history']
    assert result['valid'] and result['action'] == action
    assert all(action != row['action'] for row in history)
    assert result['status'] == 'novel_action_unchecked'
    assert result['model_calls'] == 1 and result['planning'] == result['physical'] == result['training'] == 0
    assert result['ready'] is False and result['safety_evaluated'] is False
    assert response['completion_tokens'] == len(response['generated_ids']) == 48
    assert response['prompt_tokens'] == 10725 and response['finish_reason'] == 'stop'
    config = read(RUN / 'generation_config.json')
    assert response['eos_ids'] == config['model']['eos_token_id']
    eos = response['eos_ids'] if isinstance(response['eos_ids'], list) else [response['eos_ids']]
    assert response['generated_ids'][-1] in eos
    assert [row['module'] for row in config['virtual_modules']] == ['torch.classes', 'torch.ops']
    audit = read(RUN / 'audit_result.json')
    assert audit['passed'] and audit['full_tensor_reencoding_equal']
    assert audit['checked'] == {key: result[key] for key in ('valid', 'action', 'status')}
    assert not any((RUN / name).exists() for name in ('proposal.json', 'private_plan.json', 'physical', 'execution_manifest.json'))
    return dict(status=result['status'], action=action, model_reservations_across_versions=2,
                actual_generations_across_versions=1, planning=0, physical=0, training=0,
                safety_evaluated=False, loaded_project_sources=len(config['loaded_project_sources']))


def main():
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
                  files=files(), tensors=tensors(), outcomes=outcome(), verifier_sha256=sha(Path(__file__)))
    for path, count in [(PRIOR / 'prepare-6810.log', 6), (REMOTE / 'prepare-6815.log', 4)]:
        log = path.read_text(encoding='utf-8')
        assert f'Ran {count} tests' in log and '\nOK\n' in log
    result['distinct_server_tests_passed'] = 10
    links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', (ROOT / 'REPORT.md').read_text(encoding='utf-8'))
    for link in links:
        assert (ROOT / link).is_file() or (ROOT / link).resolve() == OUTPUT
    result.update(report_links_checked=len(links), pending_current_scope=[])
    if '--write' in sys.argv:
        with OUTPUT.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    assert OUTPUT.is_file() and all((ROOT / link).is_file() for link in links)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
