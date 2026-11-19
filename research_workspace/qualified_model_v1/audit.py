"""推理完成后才读取仿真分割做私有评分；绝不修正模型坐标。"""
import cv2
import numpy as np
from qualified_model_v1.common import ROOT, PROJECT, RUN, read, save, sha, verify
from qualified_model_v1.policy import parse, pixel


def evaluate(entry):
    seed = entry['seed']
    folder, source = RUN/str(seed), PROJECT/f'qualified_task_v1/run/audit/{seed}'
    request, validated = read(entry['request']), read(folder/'validated.json')
    response = read(folder/'response.json')
    assert len(request['messages']) == 2
    assert request['image_sha256'] == sha(request['image'])
    row = dict(seed=seed, schema_valid=validated['valid'], both_correct=False,
        physical_attempts=0, model_calls=1, training_runs=0, private_evaluation_only=True)
    if not validated['valid']:
        return dict(row, status='invalid_model_response')
    prediction = parse(response)
    assert prediction == validated['parsed']
    if prediction['action'] == 'STOP':
        return dict(row, status='model_stopped')
    with np.load(source/'private_roots.npz') as data:
        roots = data['roots']
    ids = read(source/'result.json')['replay']['body_ids']
    image = cv2.imread(request['image'])
    scores = {}
    for role, name in (('source', 'PurpleCapsule'), ('destination', 'RedBin')):
        u, v = pixel(prediction[role+'_pixel'], width=roots.shape[1], height=roots.shape[0])
        scores[role] = dict(pixel=[u, v], correct=int(roots[v, u]) == ids[name])
        color = (0, 210, 0) if scores[role]['correct'] else (0, 0, 255)
        cv2.drawMarker(image, (u, v), color, cv2.MARKER_CROSS, 22, 2)
        cv2.putText(image, role, (u+8, v-8), cv2.FONT_HERSHEY_SIMPLEX, .55, color, 1)
    assert cv2.imwrite(str(folder/'grounding_audit.png'), image)
    return dict(row, status='scored', scores=scores,
                both_correct=all(s['correct'] for s in scores.values()))


def main():
    manifest = verify()
    inputs = [p for p in RUN.rglob('*') if p.is_file()]
    save(RUN/'audit_manifest.json', dict(inputs={str(p): sha(p) for p in inputs},
        audit_source_sha256=sha(ROOT/'audit.py')))
    rows = [evaluate(entry) for entry in manifest['entries']]
    verify()
    assert all(sha(p) == h for p, h in read(RUN/'audit_manifest.json')['inputs'].items())
    result = dict(rows=rows, model_calls=2, both_correct=sum(r['both_correct'] for r in rows),
        physical_attempts=0, training_runs=0, task_success_rate=None)
    save(RUN/'audit_result.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
