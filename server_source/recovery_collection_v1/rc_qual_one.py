import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from collection_common import QUAL, PARENT

sys.path.insert(0, str(PARENT/'natural_top_preflight_v1'))
import common
import span_qualify
with patch.object(common, 'ROOT', QUAL), patch.object(span_qualify, 'ROOT', QUAL):
    import one
    with patch.object(one, 'ROOT', QUAL):
        if __name__ == '__main__':
            one.main()
