"""原端点检查不变，只替换已冻结输入目录和来源校验。"""
import sys
from unittest.mock import patch
from action_space_audit_v1 import endpoints as original
from surface_grasp_v1.common import ROOT,verify


if __name__=='__main__':
    with patch.object(original,'ROOT',ROOT),patch.object(original,'verify',verify):
        original.main(sys.argv[1])
