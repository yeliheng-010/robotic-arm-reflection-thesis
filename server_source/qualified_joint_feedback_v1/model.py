import sys
from unittest.mock import patch
from qualified_feedback_v1 import model
from qualified_joint_feedback_v1.common import RUN, verify


if __name__ == '__main__':
    seed, ordinal = map(int, sys.argv[1:])
    with patch.object(model, 'RUN', RUN/str(seed)), patch.object(model, 'verify', verify):
        model.main(ordinal)
