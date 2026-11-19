import traceback
from unittest.mock import patch
import controller
from sv_common import ROOT, save

original = controller.run


def run(script, args, *, label):
    revisions = {'worker.py':'worker_v4.py', 'audit.py':'audit_v4.py'}
    return original(revisions.get(script, script), args, label=label)


if __name__ == '__main__':
    try:
        with patch.object(controller, 'run', run):
            controller.main()
    except BaseException as error:
        save(ROOT/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise
