"""从原始物理结果和双端请求日志重建pilot质量门禁。"""
import argparse
import json
from pathlib import Path
from stability.collection_status import atomic, update
from stability.collection_worker import verify_pair
from stability.dataset import examples, digest
from stability.experiment import OUT


def read(path):
    return json.loads(path.read_text())


def validate_gate(gate, configuration):
    assert gate['allow_batch'], 'Pilot quality gate failed'
    for field in ('code', 'collection_code', 'teacher'):
        assert gate[field] == configuration[field], 'Pilot identity mismatch: '+field


def audit_task(root, index, task, *, server_events, identity):
    directory = root/'tasks'/f'{index:05d}'
    summary = read(directory/'summary.json')
    assert summary['task'] == task
    paths = [Path(summary[name]).resolve() for name in ('teacher_result', 'retry_result')]
    assert all(path.is_relative_to(directory.resolve()) for path in paths)
    teacher, retry = map(read, paths)
    verify_pair(teacher, retry)
    for result in (teacher, retry):
        assert all(result[k] == v for k, v in task.items() if k != 'split')
        assert len(result['records']) <= 3
    requests = paths[0].parent/'requests.jsonl'
    events = [json.loads(line) for line in requests.read_text().splitlines()] if requests.exists() else []
    for event in events:
        if 'response' not in event:
            continue
        key = digest({'messages': event['messages']})
        assert digest(event['response']) in server_events[key]
        for name in ('model', 'architecture', 'adapter', 'thinking', 'max_new_tokens', 'decoding'):
            if name in identity:
                assert identity[name] == event['response'][name]
    rows = examples(teacher, retry, events, task_id=directory.name, split=task['split'])
    assert digest(rows) == digest(summary['samples'])
    return len(rows)


def audit(directory):
    manifest = read(directory/'manifest.json')
    assert manifest['stage'] == 'pilot'
    server_events = {}
    audit_path = Path(manifest['teacher']['audit_log']).resolve()
    assert audit_path.is_relative_to(OUT.resolve())
    for path in (audit_path,):
        for line in path.read_text().splitlines():
            event = json.loads(line)
            if 'response' in event:
                server_events.setdefault(digest(event['request']), set()).add(digest(event['response']))
    counts = [audit_task(directory, i, task, server_events=server_events, identity=manifest['teacher'])
              for i, task in enumerate(manifest['plan'])]
    status = update(directory, planned=len(manifest['plan']))
    coverage = status['by_fault']['train']
    passed = (sum(counts) >= 6 and status['service_errors'] == 0 and
              status['invalid']/max(status['calls'], 1) <= .2 and
              all(coverage.get(name, 0) >= 1 for name in ('calibration', 'collision', 'placement')))
    gate = {'allow_batch': passed, 'pilot_directory': str(directory), 'status': status,
        'manifest_sha256': digest(manifest), 'source_audit': 'client_and_server_response_match',
        'code': manifest['code'], 'collection_code': manifest['collection_code'],
        'teacher': manifest['teacher'], 'minimum_samples': 6, 'minimum_per_fault': 1}
    atomic(directory/'audit.json', gate)
    atomic(OUT/'pilot_gate.json', gate)
    return gate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    result = audit(OUT/parser.parse_args().run)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

