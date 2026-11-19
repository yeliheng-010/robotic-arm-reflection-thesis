"""真实渲染验证新Sampler：可见时发布，遮挡时阻断；不抓取。"""
import os
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene
from cv_entry import approved_config
from cc_common import ROOT, save
from cc_prepare import source, selected
from cc_runtime import GuardedSampler
from cc_policy import VisibilityRejected
from cc_audit import visibility


def main():
    output = ROOT/'smoke'/('job_'+os.environ['SLURM_JOB_ID'])
    original, _, _ = source(964294)
    config = approved_config(selected(964294), original['config'])
    arguments = dict(item=original['item'], attempt=1, success=False)
    with scene(config) as (env, _):
        good = GuardedSampler(env, config, folder=output/'clear', **arguments)
        good.capture()
        assert len(good.rows) == good.budget.count == 1
        bad = GuardedSampler(env, original['config'], folder=output/'occluded', **arguments)
        try:
            bad.capture()
        except VisibilityRejected:
            pass
        else:
            raise AssertionError('Occluded historical camera was published')
        assert bad.rows == [] and bad.budget.count == 0
        assert not (output/'occluded/observation_0').exists()
    clear = visibility(output/'clear/visibility_0.json', config)
    occluded = visibility(output/'occluded/visibility_0.json', original['config'])
    assert clear['accepted'] and not occluded['accepted']
    save(output/'result.json', dict(passed=True, clear=clear, occluded=occluded,
        physical_attempts=0, model_calls=0, rejected_public_files=0))
    print(dict(passed=True, clear=clear, occluded=occluded), flush=True)


if __name__ == '__main__':
    main()
