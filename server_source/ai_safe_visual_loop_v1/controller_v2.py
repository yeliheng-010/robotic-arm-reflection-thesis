from unittest.mock import patch
import controller

original = controller.run


def run(script, args, *, label):
    revisions = {'worker.py':'worker_v2.py', 'audit.py':'audit_v2.py'}
    return original(revisions.get(script, script), args, label=label)


if __name__ == '__main__':
    with patch.object(controller, 'run', run):
        controller.main()
