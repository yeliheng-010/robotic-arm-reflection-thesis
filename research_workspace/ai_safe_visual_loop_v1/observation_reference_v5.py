"""仅解析已有、带哈希的分支观测引用，不补写实验数据。"""
from pathlib import Path
from f_common import read, sha


def observation(step):
    folder = Path(step['session_path'])
    direct = folder/'observation_summary.json'
    if direct.exists():
        return read(direct)
    result = read(folder.parent/'result.json')
    assert step in result['ledger']['steps'], 'Step not in branch ledger'
    for ref in result['views']:
        path = Path(ref['path']).resolve()
        assert path.is_relative_to((folder.parent/'views').resolve()), 'Foreign view'
        assert sha(path) == ref['sha256'], 'View hash mismatch'
        summary = read(path)
        if summary['public'][0]['attempt'] == step['index']:
            expected = (folder.parent/'observations'/folder.name).resolve()
            assert all(Path(p).resolve().is_relative_to(expected) for p in summary['paths'])
            assert all(row['attempt'] == step['index'] for row in summary['public'])
            return summary
    raise AssertionError('No matching recorded observation')
