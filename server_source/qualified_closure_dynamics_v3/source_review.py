"""只接受明确复核、仍匹配且位于项目内的补登记文件。"""
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import read, sha, require


def load(path, project):
    record = read(path)
    require(record.get('reviewed') is True, 'Unreviewed project inventory')
    require(record.get('scope') == 'new_binding_current_state', 'Do not rewrite historical coverage')
    identities = record['identities']
    require(bool(identities), 'Empty reviewed inventory')
    for name, digest in identities.items():
        resolved = Path(name).resolve()
        require(resolved.is_relative_to(project.resolve()), 'Reviewed source outside project')
        require(sha(resolved) == digest, 'Reviewed source changed: ' + name)
    return identities
