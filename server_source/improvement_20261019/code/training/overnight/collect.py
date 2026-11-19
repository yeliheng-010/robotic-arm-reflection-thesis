"""Balanced overnight task plan with a wall-clock deadline and resumable records."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import time
import traceback
import urllib.request

from training.overnight.dataset import atomic, finalize
from training.overnight.prompt import SYSTEM, FORMAT

SOURCES = ['RedBlock', 'GreenCylinder', 'PurpleCapsule', 'OrangeSphere']
DESTINATIONS = ['BlueBin', 'RedBin', 'SortingTray']
FAULTS = ['planning', 'grounding', 'calibration', 'collision', 'placement']
# Held-out groups appear near the beginning, even if the deadline cuts the run short.
SPLITS = ['train', 'validation', 'train', 'test', 'train', 'train', 'train', 'train']


def build_plan(start_seed):
    from reflection.language import LABELS, SOURCE_ALIASES, DESTINATION_ALIASES, resolve_task
    plan = []
    for source in SOURCES:
        for destination in DESTINATIONS:
            for fault in FAULTS:
                for offset, split in enumerate(SPLITS):
                    s, d = LABELS[source], LABELS[destination]
                    en_s, en_d = SOURCE_ALIASES[source][-2], DESTINATION_ALIASES[destination][-2]
                    templates = [f'把{s}放进{d}', f'请将{s}放入{d}',
                                 f'帮我把{s}搬到{d}', f'please put the {en_s} into the {en_d}',
                                 f'请把{s}移到{d}', f'将{s}放到{d}里',
                                 f'move the {en_s} to the {en_d}', f'把{s}送到{d}']
                    instruction = templates[(offset + SOURCES.index(source) + DESTINATIONS.index(destination)) % 8]
                    resolved = resolve_task(instruction, source=source, destination=destination, parser='rule')
                    plan.append(dict(seed=start_seed+offset, split=split, source=resolved.source,
                                     destination=resolved.destination, fault=fault, instruction=instruction))
    return plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--endpoint', default='http://127.0.0.1:18766')
    parser.add_argument('--deadline', type=float, required=True, help='UTC Unix epoch')
    parser.add_argument('--start-seed', type=int, default=2000)
    args = parser.parse_args()
    from reflection.__main__ import bootstrap
    bootstrap()
    from reflection.engine import FeedbackEngine
    from training.qlora import data
    data.SYSTEM = SYSTEM
    from training.server.collect import LocalReflector
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = {k: v for k, v in vars(args).items() if k != 'output'}
    config.update(scene_jitter=.012, max_attempts=3, prompt_format=FORMAT)
    fingerprints = {str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest()
        for directory in ('reflection', 'training/overnight', 'training/server', 'training/qlora')
        for f in (root/directory).glob('*.py')}
    for name in ('grasp_process.py', 'manipulator_grasp/env/ur5_grasp_env.py'):
        fingerprints[name] = hashlib.sha256((root/name).read_bytes()).hexdigest()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(args.endpoint+'/health', timeout=10) as response:
        teacher = json.load(response)
    if not teacher.get('frozen') or teacher.get('adapter') is not None or teacher.get('prompt_format') != FORMAT:
        raise RuntimeError('Wrong teacher identity or prompt format')
    manifest = {'config': config, 'code_sha256': fingerprints, 'teacher': teacher,
                'prompt_system_sha256': hashlib.sha256(SYSTEM.encode()).hexdigest()}
    path = output/'manifest.json'
    plan = build_plan(args.start_seed)
    if path.exists():
        old = json.loads(path.read_text())
        for key in ('config', 'code_sha256', 'prompt_system_sha256'):
            if old[key] != manifest[key]:
                raise RuntimeError('Configuration/code changed; use a new output directory')
        for key in ('model', 'adapter', 'frozen', 'prompt_format'):
            if old['teacher'][key] != teacher[key]:
                raise RuntimeError('Teacher identity changed')
        if json.loads((output/'plan.json').read_text()) != plan:
            raise RuntimeError('Task plan changed')
    else:
        atomic(output/'plan.json', plan)
        atomic(path, manifest)
    stop_requested = []
    def stop(signum, frame):
        stop_requested.append(signum)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    reason = 'completed'
    consecutive_errors = 0
    finalize(output)
    try:
        for index, task in enumerate(plan):
            if stop_requested or time.time() >= args.deadline:
                reason = 'signal' if stop_requested else 'morning_deadline'
                break
            directory = output/'tasks'/f'{index:05d}'
            if (directory/'result.json').exists() or (directory/'error.json').exists():
                continue
            print(f'[overnight] {index+1}/{len(plan)} '+json.dumps(task, ensure_ascii=False), flush=True)
            engine = None
            try:
                engine = FeedbackEngine(reflector=LocalReflector(task['instruction'], args.endpoint),
                    headless=True, task_parser='rule', perception='simulation', segmentation='simulation',
                    grasp_backend='geometric', max_attempts=3, scene_jitter=.012)
                engine.run(**{k: v for k, v in task.items() if k != 'split'}, method='reflection',
                    output=directory, context='server-overnight-v2')
                consecutive_errors = 0
            except Exception as error:
                atomic(directory/'error.json', {'task': task, 'error': str(error),
                    'traceback': traceback.format_exc(), 'time': time.time()})
                consecutive_errors += 1
            finally:
                if engine is not None:
                    engine.close()
                print(json.dumps(finalize(output), ensure_ascii=False), flush=True)
            if consecutive_errors >= 5:
                reason = 'five_consecutive_task_errors'
                break
    except BaseException:
        reason = 'collector_exception'
        raise
    finally:
        print(json.dumps(finalize(output, reason), ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
