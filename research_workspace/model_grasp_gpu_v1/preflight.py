import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from cc_audit import visibility
from model_grasp_gpu_v1.common import ROOT, SOURCE, read, save, sha, verify
from model_grasp_gpu_v1.observed import prepare
from model_grasp_intent_v1.requests import build, messages
from model_grasp_gpu_v1.common import BUDGET


def main():
    manifest = verify()
    assert manifest['case']['item']['seed'] == 964347
    assert manifest['case']['config']['group'] == 'varied_noisy'
    checked = visibility(SOURCE/'initial_visibility.json', manifest['case']['config'])
    assert checked['accepted']
    calibration = read(SOURCE/'span_guard.json')
    plan = read(SOURCE/'actual_plan.json')
    with np.load(SOURCE/'span_inputs.npz') as arrays:
        with np.load(SOURCE/'execution/attempt_1/depth_evidence.npz') as evidence:
            np.testing.assert_array_equal(arrays['depth'], evidence['noisy'])
        nominal = np.asarray(plan['context']['nominal'])[:3,3]
        observation = prepare(arrays, calibration, nominal)
    save(ROOT/'observation.json', observation)
    request = build(observation, BUDGET, history=[], can_observe=False)
    save(ROOT/'request_preview.json', dict(request=request, messages=messages(request)))
    save(ROOT/'preflight.json', dict(passed=True, visibility=checked, noisy_depth_identical=True,
         target_points=len(observation['target_points']), scene_points=len(observation['scene_points']),
         observation_sha256=sha(ROOT/'observation.json'), source_sha256=sha(SOURCE/'span_inputs.npz'),
         image_sha256=sha(SOURCE/'execution/attempt_1/before.png'),
         physical_attempts=0, model_calls=0, phase=manifest['phase']))
    print(dict(preflight=True, target_points=len(observation['target_points']),
               scene_points=len(observation['scene_points'])), flush=True)


if __name__ == '__main__':
    main()
