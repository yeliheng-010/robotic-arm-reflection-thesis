"""本地归档检查；不加载模型、仿真，不重跑服务器测试。"""
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
EVIDENCE = ROOT / 'evidence'
REMOTE = EVIDENCE / 'remote'
RUN = REMOTE / 'run'
OUTPUT = EVIDENCE / 'FINAL_VERIFICATION.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files():
    delivery = read(EVIDENCE / 'DELIVERY.json')['files']
    seen, sources = set(), 0
    for row in delivery:
        path = (REMOTE / row['path']).resolve()
        assert path.is_relative_to(REMOTE.resolve())
        assert row['path'] not in seen and row['sha256'] == sha(path)
        seen.add(row['path'])
        if len(Path(row['path']).parts) == 1 and path.suffix in ('.py', '.md', '.json', '.sh', '.sbatch'):
            assert row['sha256'] == sha(ROOT / row['path'])
            sources += 1
    recovery = ROOT.parent / 'qualified_prompt_checkpoint_v2/evidence/remote/run/manifest.json'
    identities = read(recovery)['identities']
    for row in delivery:
        key = '/home/yeliheng/grasp_server/qualified_prompt_checkpoint_v1/' + row['path']
        assert identities[key] == row['sha256']
    old = ROOT.parent / 'qualified_execution_v1/evidence/remote/run/attempt_claim.json'
    assert read(old)['consumed'] == 1
    assert identities['/home/yeliheng/grasp_server/qualified_execution_v1/run/attempt_claim.json'] == sha(old)
    return dict(downloaded=len(seen), byte_identical_sources=sources, old_claim_unchanged=True)


def request_check():
    old = ROOT.parent / 'qualified_closure_feedback_v1/evidence/remote/run/decision_2/request.json'
    original, request = read(old), read(RUN / 'request.json')
    body, before = [json.loads(r['messages'][1]['content']) for r in (request, original)]
    checkpoint = body.pop('decision_checkpoint')
    draft = json.loads(read(ROOT / 'B_checkpoint.json')['request']['messages'][1]['content'])
    assert checkpoint == draft['decision_checkpoint']
    assert checkpoint['latest_public_rejection'] == before['history'][-1]
    assert body['budget'] == dict(decisions=1, planning=0, observations=0)
    body['budget'] = before['budget']
    assert body == before
    request['messages'][1]['content'] = original['messages'][1]['content']
    assert request == original
    image = ROOT.parent / 'qualified_task_v1/evidence/images/audit/978505/qualified.png'
    assert read(RUN / 'manifest.json')['identities'][request['image']] == sha(image)
    return before['history']


def arrays():
    saved = read(RUN / 'encoding.json')
    assert saved['npz_sha256'] == sha(RUN / 'input_tensors.npz')
    with zipfile.ZipFile(RUN / 'input_tensors.npz') as archive:
        assert {n[:-4] for n in archive.namelist()} == set(saved['tensors'])
        for name in archive.namelist():
            blob = archive.read(name)
            assert blob[:6] == b'\x93NUMPY' and blob[6:8] == b'\x01\x00'
            size = struct.unpack('<H', blob[8:10])[0]
            header = ast.literal_eval(blob[10:10 + size].decode('latin1'))
            payload, key = blob[10 + size:], name[:-4]
            assert header['fortran_order'] is False
            assert list(header['shape']) == saved['tensors'][key]['shape']
            assert hashlib.sha256(payload).hexdigest() == saved['tensors'][key]['sha256']
            if key in ('input_ids', 'attention_mask'):
                assert header['descr'] == '<i8'
                values = list(struct.unpack('<' + str(len(payload) // 8) + 'q', payload))
                assert saved[key] == [values]
    templates = read(RUN / 'templates.json')
    body_text = read(RUN / 'request.json')['messages'][1]['content']
    assert body_text in templates['decoded_input']
    return dict(keys=sorted(saved['tensors']), input_tokens=saved['encoding']['input_tokens'],
                saved_tensor_hashes_checked=True, decoded_public_body_present=True)


def outcome(history):
    result = read(RUN / 'failure_audit.json')
    claim = read(RUN / 'model_claim.json')
    assert claim == dict(ordinal=1, consumed=1, request_sha256=sha(RUN / 'request.json'))
    assert result['passed'] and result['full_tensor_reencoding_equal']
    assert result['model_calls'] == result['generations_started'] == result['responses_saved'] == 0
    assert all(not (RUN / name).exists() for name in result['absent_files'])
    assert result['model_source_sha256'] == sha(REMOTE / 'model.py')
    assert result['failure_log_sha256'] == sha(REMOTE / 'run-6811.log')
    assert result['auditor_sha256'] == sha(REMOTE / 'failure_audit_v2.py')
    source = (REMOTE / 'model.py').read_text(encoding='utf-8')
    assert source.index('record(generator, values') < source.index('generator.generate(values)')
    return dict(status='pre_generation_engineering_failure', model_reservations=1, model_calls=0,
                planning=0, physical=0, training=0, failure_audit_passed=True)


def main():
    checked_files = files()
    history = request_check()
    tensor_info, result = arrays(), outcome(history)
    log = (REMOTE / 'prepare-6810.log').read_text(encoding='utf-8')
    assert 'Ran 6 tests' in log and '\nOK\n' in log
    targets = [(ROOT / value).resolve() for value in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',
                (ROOT / 'REPORT.md').read_text(encoding='utf-8'))]
    assert all(p.is_file() or p == OUTPUT for p in targets)
    value = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True, files=checked_files,
                 tensors=tensor_info, outcomes=result, server_tests_passed=6,
                 report_links_checked=len(targets), local_new_model_calls=0,
                 verifier_sha256=sha(Path(__file__)), pending_current_scope=[])
    if '--write' in sys.argv:
        with OUTPUT.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    assert OUTPUT.is_file() and all(p.is_file() for p in targets)
    print(json.dumps(value, ensure_ascii=True))


if __name__ == '__main__':
    main()
