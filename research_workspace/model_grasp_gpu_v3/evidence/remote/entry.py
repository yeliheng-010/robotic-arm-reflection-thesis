import sys
from unittest.mock import patch
from model_grasp_gpu_v1.common import read
from model_grasp_gpu_v3.scope import ROOT, bind
from model_grasp_gpu_v3.prompt import pack, messages


def main(mode):
    if mode == 'tokens':
        from model_grasp_gpu_v2 import token_check
        with bind(token_check),patch.object(token_check,'pack',pack),patch.object(token_check,'messages',messages):
            token_check.main()
        return
    assert read(ROOT/'token_gate.json')['passed']
    if mode == 'model':
        from model_grasp_gpu_v1 import model_call
        with bind(model_call),patch.object(model_call,'messages',messages):
            model_call.main(int(sys.argv[2]))
        return
    execute(mode)


def execute(mode):
    from model_grasp_gpu_v1 import controller, planning, audit
    original = controller.Callbacks.policy
    def policy(self, request):
        return original(self,pack(request))
    with bind(controller,planning,audit),patch.object(controller.Callbacks,'policy',policy):
        if mode == 'controller':
            controller.main()
        elif mode == 'audit':
            audit.main()
        else:
            raise ValueError('Unknown stage')


if __name__ == '__main__':
    main(sys.argv[1])
