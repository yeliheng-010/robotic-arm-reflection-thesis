"""复用已验证的记录逻辑，替换不兼容的平行指垫假设。"""
from unittest.mock import patch
from qualified_closure_v1 import worker as original
from qualified_closure_v2.common import RUN, freeze, verify
from qualified_closure_v2.geometry import sweep


def main():
    with patch.multiple(original, RUN=RUN, freeze=freeze, verify=verify, sweep=sweep):
        original.main()


if __name__ == '__main__':
    main()
