import subprocess
import traceback
from model_grasp_intent_v1.loop import run
from model_grasp_gpu_v1.common import ROOT, BUDGET, read, save, sha, verify
from model_grasp_gpu_v1.planning import inspect


class Callbacks:
    def __init__(self, manifest):
        self.manifest, self.decisions, self.plans = manifest, 0, 0

    def policy(self, request):
        self.decisions += 1
        folder = ROOT/'run'/f'decision_{self.decisions}'
        save(folder/'request.json',request)
        with (folder/'model.log').open('x') as log:
            result = subprocess.run(['bash',str(ROOT/'model.sh'),str(self.decisions)],
                stdout=log,stderr=subprocess.STDOUT,timeout=self.manifest['model_process_timeout_s'])
        save(folder/'process.json',dict(exit_code=result.returncode))
        assert result.returncode == 0, 'Model process rejected; inspect private log'
        return read(folder/'validated_response.json')

    def planner(self, proposal):
        self.plans += 1
        folder = ROOT/'run'/f'plan_{self.plans}'
        save(folder/'proposal.json',proposal)
        try:
            result = inspect(proposal,self.manifest,folder)
        except Exception:
            save(folder/'private_error.json',dict(traceback=traceback.format_exc()))
            raise
        save(folder/'result.json',result)
        return result


def main():
    manifest = verify()
    gate = read(ROOT/'preflight.json')
    assert gate['passed'] and sha(ROOT/'observation.json') == gate['observation_sha256']
    save(ROOT/'run/started.json',dict(manifest_sha256=sha(ROOT/'manifest.json'),budget=BUDGET))
    callbacks = Callbacks(manifest)
    result = run(read(ROOT/'observation.json'),callbacks.policy,callbacks.planner,budget=BUDGET)
    result.update(real_model_calls=len(list((ROOT/'run').glob('decision_*/generation_started.json'))),
                  model_processes=callbacks.decisions, planning_callbacks=callbacks.plans,
                  source='frozen_qualified_observation', manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/'run/result.json',result)
    print({k:v for k,v in result.items() if k!='history'},flush=True)
    assert result['status'] not in ('policy_error','planner_error','observation_error')


if __name__ == '__main__':
    main()
