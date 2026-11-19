"""只切换严格审计版本，保持原采集数量和种子政策。"""
from unittest.mock import patch
from iv3_audit import ROOT, BASE
from collection_common import verify
import ig_next


def main():
    verify(BASE / 'source_manifest.json')
    with patch.object(ig_next, 'ROOT', ROOT):
        ig_next.main()


if __name__ == '__main__':
    main()
