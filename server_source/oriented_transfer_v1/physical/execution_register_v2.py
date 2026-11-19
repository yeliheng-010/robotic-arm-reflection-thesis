from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import execution_register
from op_worker_v2 import TRIAL

if __name__=='__main__':
    with patch.object(execution_register,'TRIAL',TRIAL):
        execution_register.main()
