"""Resumable headless collection with frozen local teacher and physical verification."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from reflection.__main__ import bootstrap
from training.qlora.data import make_messages


def atomic(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    tmp.replace(path)


class LocalReflector:
    def __init__(self, instruction, endpoint):
        self.instruction, self.endpoint = instruction, endpoint

    def reflect(self, report, parameters, history=()):
        from reflection.reflector import Reflection
        messages = make_messages(self.instruction, report.to_dict(), parameters.to_dict(), history, {})[:-1]
        req = urllib.request.Request(self.endpoint+'/reflect',
            data=json.dumps({'messages': messages}, ensure_ascii=False).encode(),
            headers={'Content-Type': 'application/json'})
        # Local loopback must not inherit a desktop proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=240) as response:
                data = json.load(response)
        except Exception as e:
            raise RuntimeError('Local teacher request failed: '+str(e)) from e
        raw = data['text'].strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        result = json.loads(raw)
        if not isinstance(result.get('cause'), str) or not result['cause'].strip():
            raise ValueError('Teacher returned no cause')
        parameters.updated(result.get('changes'))
        return Reflection(result['cause'], result['changes'], 'llm')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--endpoint', default='http://127.0.0.1:18765')
    p.add_argument('--mode', choices=['teacher', 'rule'], default='teacher')
    p.add_argument('--seeds', type=int, default=2)
    p.add_argument('--start-seed', type=int, default=1000)
    p.add_argument('--faults', nargs='+', default=['planning', 'grounding', 'calibration', 'collision', 'placement'])
    p.add_argument('--sources', nargs='+', default=['RedBlock', 'GreenCylinder'])
    p.add_argument('--destinations', nargs='+', default=['BlueBin', 'RedBin', 'SortingTray'])
    p.add_argument('--scene-jitter', type=float, default=.012)
    a = p.parse_args()
    if a.seeds < 1:
        p.error('--seeds must be positive')
    bootstrap()
    from reflection.engine import FeedbackEngine
    from reflection.reflector import RuleReflector
    from reflection.language import LABELS
    from training.qlora.export_verified import verified_examples
    a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=True)
    config = {k: v for k, v in vars(a).items() if k != 'output'}
    fingerprints = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest()
        for directory in ('reflection', 'training/server', 'training/qlora')
        for f in (ROOT/directory).glob('*.py')}
    for f in [ROOT/'grasp_process.py', ROOT/'manipulator_grasp/env/ur5_grasp_env.py']:
        fingerprints[str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    frozen = {'config': config, 'code_sha256': fingerprints}
    manifest_path = a.output/'manifest.json'
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if any(old[k] != frozen[k] for k in frozen):
            raise RuntimeError('Configuration/code changed; use a new output directory')
        teacher = old['teacher']
        if a.mode == 'teacher':
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(a.endpoint+'/health', timeout=10) as r:
                current_teacher = json.load(r)
            if any(current_teacher[k] != teacher[k] for k in ('model', 'adapter', 'prompt_format', 'frozen')):
                raise RuntimeError('Teacher identity changed; use a new output directory')
    else:
        teacher = {'model': 'rule', 'purpose': 'mechanism baseline, excluded from LLM training'}
        if a.mode == 'teacher':
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(a.endpoint+'/health', timeout=10) as r:
                teacher = json.load(r)
        atomic(manifest_path, {**frozen, 'teacher': teacher, 'created': time.time(),
            'provenance': 'Local frozen model, simulation perception/segmentation, geometric grasp, no visual veto',
            'preflight': {'model_id': teacher['model']}})
    plan = []
    for seed in range(a.start_seed, a.start_seed+a.seeds):
        for source in a.sources:
            for destination in a.destinations:
                for fault in a.faults:
                    plan.append({'seed': seed, 'source': source, 'destination': destination, 'fault': fault})
    atomic(a.output/'plan.json', plan)

    def progress():
        results = []
        examples = []
        seen = set()
        for f in sorted((a.output/'tasks').glob('*/result.json')):
            result = json.loads(f.read_text())
            results.append(result)
            for row in verified_examples(result, f.relative_to(a.output)):
                digest = hashlib.sha256(json.dumps(row['messages'], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                row['metadata'].update(sample_sha256=digest, teacher_model=teacher['model'],
                    result_sha256=hashlib.sha256(f.read_bytes()).hexdigest(), prompt_format='text-reflection-v1')
                examples.append(row)
        data = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in examples)
        tmp = a.output/'verified_train.jsonl.tmp'
        tmp.write_text(data)
        tmp.replace(a.output/'verified_train.jsonl')
        summary = {'planned_tasks': len(plan), 'completed_tasks': len(results),
            'successful_tasks': sum(r['success'] for r in results),
            'reflection_calls': sum('reflection' in rec for r in results for rec in r['records']),
            'invalid_reflections': sum('reflection_error' in rec for r in results for rec in r['records']),
            'unique_verified_samples': len(examples),
            'verified_by_fault': dict(Counter(x['metadata']['fault'] for x in examples)),
            'teacher_model': teacher['model'], 'mode': a.mode, 'updated': time.time(),
            'dataset_sha256': hashlib.sha256(data.encode()).hexdigest(),
            'limitation': 'Pilot pool only, unsplit; repeated toy-scene evidence is not an independent efficacy evaluation.'}
        atomic(a.output/'status.json', summary)
        return summary

    progress()
    for index, task in enumerate(plan):
        directory = a.output/'tasks'/f'{index:05d}'
        if (directory/'result.json').exists():
            continue
        instruction = f"把{LABELS[task['source']]}放进{LABELS[task['destination']]}"
        reflector = LocalReflector(instruction, a.endpoint) if a.mode == 'teacher' else RuleReflector()
        engine = FeedbackEngine(reflector=reflector, headless=True, task_parser='rule',
            perception='simulation', segmentation='simulation', grasp_backend='geometric',
            max_attempts=3, scene_jitter=a.scene_jitter)
        print(f'[collection] {index+1}/{len(plan)} '+json.dumps(task), flush=True)
        try:
            engine.run(**task, instruction=instruction, method='reflection', output=directory,
                context='server-pilot-v1')
        finally:
            engine.close()
        print(json.dumps(progress(), ensure_ascii=False), flush=True)
    print(json.dumps(progress(), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
