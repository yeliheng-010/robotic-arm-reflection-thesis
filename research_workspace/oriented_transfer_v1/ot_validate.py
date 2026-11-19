import unittest
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import test_geometry
import test_volume
import test_numeric
from ot_volume_v2 import context,place


if __name__=='__main__':
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m)
        for m in (test_geometry,test_volume,test_numeric))
    with context(),patch.object(test_volume,'place',place):
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
