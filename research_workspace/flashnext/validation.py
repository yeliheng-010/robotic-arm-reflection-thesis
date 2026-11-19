"""冻结 validation 的离线评估；不接触封存 test。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from reflection.reflector import Parameters
from stability.collection_status import atomic
from flashnext.client import generate, parse_correction, ready, append
from flashnext.provenance import identity

DATA = Path('/home/yeliheng/grasp_server/stability_20261019/round2_sft_data_v1')
ROOT = Path('/home/yeliheng/grasp_server/flashnext_v1')


def dataset():
    raw = (DATA/'validation.jsonl').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    manifest = json.loads((DATA/'manifest.json').read_text())
    assert digest == manifest['files']['validation']['sha256']
    rows = [json.loads(s) for s in raw.decode().splitlines()]
    assert len(rows) == 294
    return rows, digest


def evaluate(index, row, *, budget):
    event = generate(row['messages'][:-1], max_tokens=budget)
    expected = json.loads(row['messages'][-1]['content'])
    event.update(index=index, metadata=row['metadata'], expected=expected,
                 legal=False, exact=False, json_with_changes=False)
    try:
        raw = event['response']['choices'][0]['message']['content']
        parsed = json.loads(raw)
        event['json_with_changes'] = isinstance(parsed, dict) and isinstance(parsed.get('changes'), dict)
        event['exact'] = event['json_with_changes'] and parsed['changes'] == expected['changes']
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    try:
        if 'error' in event:
            raise ValueError(event['error'])
        payload = json.loads(row['messages'][1]['content'])
        current = Parameters().updated(payload['parameters'])
        count = payload['error']['evidence'].get('diagnostics', {}).get('available_candidate_count')
        answer = parse_correction(event['text'], current, candidate_count=count)
        event.update(legal=True, parsed=answer.to_dict())
    except (ValueError, TypeError, KeyError) as error:
        event['parse_error'] = str(error)
    return event


def metrics(events):
    return dict(samples=len(events), legal=sum(e['legal'] for e in events),
                exact=sum(e['exact'] for e in events),
                json_with_changes=sum(e['json_with_changes'] for e in events),
                service_errors=sum(e.get('service_error', False) for e in events),
                truncated=sum(e.get('response', {}).get('choices', [{}])[0].get('finish_reason')
                              == 'length' for e in events))


def run(mode):
    rows, digest = dataset()
    selected = list(enumerate(rows))
    if mode == 'smoke':
        seen, selected = set(), []
        for index, row in enumerate(rows):
            fault = row['metadata']['fault']
            if fault not in seen:
                selected.append((index, row))
                seen.add(fault)
    directory = ROOT/('smoke256' if mode == 'smoke' else 'validation256')
    directory.mkdir(exist_ok=False)
    result = dict(status='running', validation_sha256=digest, expected_samples=len(selected),
                  max_tokens=256, test_used=False, physics_evaluated=False,
                  job=os.environ.get('SLURM_JOB_ID'), started_at=time.time(), models=ready(),
                  provenance=identity())
    events, outages = [], 0
    atomic(directory/'progress.json', result)
    try:
        for index, row in selected:
            event = evaluate(index, row, budget=256)
            append(directory/'responses.jsonl', event)
            events.append(event)
            outages = outages+1 if event.get('service_error') else 0
            result['metrics'] = metrics(events)
            atomic(directory/'progress.json', result)
            print(json.dumps(result['metrics']), flush=True)
            if outages >= 3:
                raise RuntimeError('Three consecutive service failures; halted')
        result.update(status='completed', by_fault={f: metrics([e for e in events
            if e['metadata']['fault'] == f]) for f in ('calibration', 'collision', 'placement')})
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        result['ended_at'] = time.time()
        atomic(directory/'result.json', result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['smoke', 'full'], required=True)
    run(parser.parse_args().mode)
