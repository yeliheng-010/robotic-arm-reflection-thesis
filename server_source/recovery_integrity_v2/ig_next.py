"""复用原扩量政策，仅替换物理审计与后续调度入口。"""
import sys
from pathlib import Path
from unittest.mock import patch
from collection_common import verify

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'collection_scale_v1'))
import sc_next

REPLACEMENTS = {'physical_shards.sbatch', 'physical_merge.sbatch', 'next.sbatch'}


def main():
    verify(ROOT / 'source_manifest.json')
    submit = sc_next.submit

    def redirected(script, folder, **kwargs):
        destination = ROOT / script.name if script.name in REPLACEMENTS else script
        return submit(destination, folder, **kwargs)

    with patch.object(sc_next, 'submit', redirected):
        sc_next.main()


if __name__ == '__main__':
    main()
