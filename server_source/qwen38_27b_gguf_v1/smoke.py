"""验证独立GGUF端点，保留原始输出；不读取封存test、不修补答案。"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

from reflection.reflector import Parameters
from stability.prompt import parse_response

ROOT = Path('/home/yeliheng/grasp_server/qwen38_27b_gguf_v1')
DATA = Path('/home/yeliheng/grasp_server/stability_20261019/round2_sft_data_v1')
BASE = 'http://127.0.0.1:38271'
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MAX_WAIT = 900
MAX_NEW_TOKENS = 256
TARGET = ROOT/f"smoke-{os.environ.get('SLURM_JOB_ID', 'nojob')}.json"


def request(path, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload else None
    req = urllib.request.Request(BASE+path, data=body,
        headers={'Content-Type': 'application/json'})
    with OPENER.open(req, timeout=MAX_WAIT) as response:
        return json.load(response)


def wait_ready():
    deadline = time.monotonic()+MAX_WAIT
    while time.monotonic() < deadline:
        try:
            if request('/health').get('status') == 'ok':
                return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(3)
    raise TimeoutError('Model did not become healthy within 900 seconds')


def generate(messages):
    payload = dict(model='qwen3.8-27b-q4', messages=messages, temperature=0,
        max_tokens=MAX_NEW_TOKENS, seed=42,
        chat_template_kwargs={'enable_thinking': False})
    start = time.monotonic()
    response = request('/v1/chat/completions', payload)
    choice = response['choices'][0]
    content = choice['message'].get('content')
    assert isinstance(content, str) and content.strip(), 'Empty model response'
    return dict(request=payload, response=response, elapsed_s=time.monotonic()-start,
        content=content, finish_reason=choice['finish_reason'])


def development_examples():
    raw = (DATA/'validation.jsonl').read_bytes()
    manifest = json.loads((DATA/'manifest.json').read_text())
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == manifest['files']['validation']['sha256']
    selected, seen = [], set()
    for index, line in enumerate(raw.decode().splitlines()):
        row = json.loads(line)
        fault = row['metadata']['fault']
        if fault not in seen:
            selected.append((index, row))
            seen.add(fault)
    assert seen == {'calibration', 'collision', 'placement'}
    return selected, digest


def reflection_example(index, row):
    result = generate(row['messages'][:-1])
    result.update(index=index, task_id=row['metadata']['task_id'], fault=row['metadata']['fault'])
    result['expected'] = json.loads(row['messages'][-1]['content'])
    try:
        payload = json.loads(row['messages'][1]['content'])
        parameters = Parameters().updated(payload['parameters'])
        answer = parse_response(result['content'], parameters)
        candidates = payload['error']['evidence'].get('diagnostics', {}).get('available_candidate_count')
        if 'candidate_index' in answer.changes and candidates is not None:
            assert answer.changes['candidate_index'] < candidates, 'Unavailable candidate'
        result.update(legal_correction=True, parsed=answer.to_dict(),
            changes_exact_match=answer.changes == result['expected']['changes'])
    except (ValueError, TypeError, KeyError, AssertionError) as error:
        result.update(legal_correction=False, changes_exact_match=False, parse_error=str(error))
    return result


def save(result):
    temporary = TARGET.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    temporary.replace(TARGET)


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Run through Slurm'
    assert not TARGET.exists(), 'Preserve previous smoke'
    result = dict(status='running', job=os.environ['SLURM_JOB_ID'], started_at=time.time(),
        cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'), test_used=False,
        physics_evaluated=False, scope='Three development examples, not a benchmark', reflections=[])
    save(result)
    try:
        wait_ready()
        result['models'] = request('/v1/models')
        assert any(m['id'] == 'qwen3.8-27b-q4' for m in result['models']['data'])
        result['basic'] = generate([{'role': 'user', 'content': '请用一句中文介绍你能如何帮助分析机械臂抓取失败。'}])
        rows, digest = development_examples()
        result['validation_sha256'] = digest
        for index, row in rows:
            result['reflections'].append(reflection_example(index, row))
            save(result)
        result['gpu_snapshot'] = subprocess.check_output(['nvidia-smi',
            '--query-gpu=index,name,memory.used,utilization.gpu', '--format=csv'], text=True)
        result.update(status='completed', ended_at=time.time(),
            legal_corrections=sum(r['legal_correction'] for r in result['reflections']),
            exact_matches=sum(r['changes_exact_match'] for r in result['reflections']))
    except BaseException as error:
        result.update(status='failed', error=repr(error), ended_at=time.time())
        raise
    finally:
        save(result)
    print(json.dumps({k: result[k] for k in ('status', 'job', 'legal_corrections', 'exact_matches')}), flush=True)


if __name__ == '__main__':
    main()

