import os
from types import SimpleNamespace
from pathlib import Path
import numpy as np
from PIL import Image
from reflection.__main__ import bootstrap
bootstrap()
from nc_common import verify as verify_base
from nc_state import Branch
from nc_requests import build
from live_telemetry import Recorder
from public_execution import public
from prompts import messages
from mm_common import ROOT, SOURCE, CASE, read, save, sha

PADDING_PX = 48
MIN_ROI_PIXELS = 10


def images(summary):
    folder = Path(summary['paths'][0])
    rgb = folder/'rgb.png'
    assert sha(rgb) == summary['private'][0]['rgb_sha256']
    paths = [rgb]
    with np.load(folder/'private_sensor.npz') as arrays:
        ys, xs = np.nonzero(arrays['source_mask'])
    bounds = None
    with Image.open(rgb) as image:
        if len(xs) >= MIN_ROI_PIXELS:
            bounds = [max(0, int(xs.min())-PADDING_PX), max(0, int(ys.min())-PADDING_PX),
                      min(image.width, int(xs.max())+PADDING_PX+1), min(image.height, int(ys.max())+PADDING_PX+1)]
            path = ROOT/'source_neighborhood.png'
            assert not path.exists()
            image.crop(bounds).save(path)
            paths.append(path)
    return dict(paths=[str(p) for p in paths], sha256=[sha(p) for p in paths], crop_bounds=bounds,
                crop_source='existing_simulation_segmentation_mask', original_rgb=str(rgb))


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'manifest.json').exists()
    base = verify_base()
    source_manifest = read(SOURCE/'manifest.json')
    audit = read(SOURCE/'audit_962501.json')
    assert audit['passed'] and audit['manifest_sha256'] == sha(SOURCE/'manifest.json')
    folder = SOURCE/'cases'/CASE/'attempt_1'
    case = next(c for c in source_manifest['cases'] if c['item']['id']==CASE)
    selected = [p for p in folder.rglob('*') if p.is_file()]
    assert all(sha(p) == audit['identities'][str(p)] for p in selected)
    step = read(folder/'step.json')
    assert not step['success'] and step['index'] == 1
    summary = read(folder/'observation_summary.json')
    recorder = Recorder()
    recorder.rows = read(folder/'telemetry.json')['rows']
    session = SimpleNamespace(record=read(step['result_path'])['records'][0], recorder=recorder)
    bundle = build(Branch(case['item'], step), session, SimpleNamespace(sampler=SimpleNamespace(rows=summary['public'])))
    request = bundle['request']
    request['evidence'].append(dict(id=f"e{len(request['evidence'])+1}", field='execution_facts',
        value=public(step, read(folder/'bridge.json')), source='command_runtime_and_task_evaluator'))
    visual = images(summary)
    request['evidence'].append(dict(id=f"e{len(request['evidence'])+1}", field='attached_rgb_images',
        value=['full_camera_frame', 'source_neighborhood_crop'][:len(visual['paths'])], source='saved_first_rgb_frame'))
    request['sensing_status']['rgb'] = 'attached_full_frame_and_mask_assisted_crop'
    request['version'] = 'visual-input-smoke-v1'
    save(ROOT/'input.json', dict(request=request, visual=visual,
        direct_messages=messages(request, mode='direct'), diagnostic_messages=messages(request, mode='diagnostic')))
    identities = dict(base['identities'])
    facts = ROOT.parent/'ai_observable_facts_v1/public_execution.py'
    artifacts = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md', '.json', '.png')]
    for path in [*selected, SOURCE/'manifest.json', SOURCE/'audit_962501.json', facts, *artifacts]:
        if path.is_file():
            identities[str(path)] = sha(path)
    save(ROOT/'manifest.json', dict(identities=identities, model_calls=2, new_physical_attempts=0,
        training_ready=False, source_condition=CASE, source_attempt=1))
    print(dict(images=len(visual['paths']), frozen=sha(ROOT/'manifest.json')), flush=True)


if __name__ == '__main__':
    main()
