"""冻结闭环任务、物理身份、训练产物和评估代码。"""
import json
from stability.collection_status import atomic
from stability.experiment import OUT, THREADS
from stability.expert_config import configuration
from stability.sft_freeze import file_hash
from stability.loop_protocol import plan, ARMS, MAX_NEW_TOKENS, WORKERS

ROOT = OUT/'closed_loop_v1'
FILES = ('loop_protocol.py', 'loop_freeze.py', 'loop_client.py', 'loop_service.py',
         'loop_worker.py', 'loop_run.py', 'loop_audit.py', 'sft_model.py', 'sft_freeze.py')


def identity():
    training = OUT/'pilot_sft_v1'
    config = json.loads((training/'manifest.json').read_text())
    result = json.loads((training/'result.json').read_text())
    assert result['status'] == 'completed'
    adapter = training/'adapter'
    actual = {n: file_hash(adapter/n) for n in result['adapter_files']}
    assert actual == result['adapter_files']
    return dict(purpose='six_new_scene_development_closed_loop_not_final_test', tasks=plan(), arms=ARMS,
        physics=configuration('batch'), model=config['model'], adapter=str(adapter), adapter_files=actual,
        training_manifest_sha256=file_hash(training/'manifest.json'), threads=THREADS,
        code={n: file_hash(OUT/'stability'/n) for n in FILES}, max_attempts=3, scene_jitter=.012,
        decoding=dict(do_sample=False, thinking=False, max_new_tokens=MAX_NEW_TOKENS), workers=WORKERS,
        baseline='same_NF4_base_with_all_adapters_disabled', test_used=False)


def verify():
    expected = json.loads((ROOT/'manifest.json').read_text())
    assert expected == json.loads(json.dumps(identity())), 'Frozen closed-loop identity changed'
    return expected


def main():
    config = identity()
    ROOT.mkdir(exist_ok=False)
    atomic(ROOT/'manifest.json', config)
    print(json.dumps({'root': str(ROOT), 'cases': len(config['tasks']), 'arms': ARMS}))


if __name__ == '__main__':
    main()
