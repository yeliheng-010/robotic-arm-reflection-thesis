import traceback
from unittest.mock import patch
import mm_common
import mm_run


if __name__ == '__main__':
    target = mm_common.ROOT/'temporal_v2'
    try:
        with patch.object(mm_common, 'ROOT', target), patch.object(mm_run, 'ROOT', target):
            mm_run.main()
    except BaseException as error:
        mm_common.save(target/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise
