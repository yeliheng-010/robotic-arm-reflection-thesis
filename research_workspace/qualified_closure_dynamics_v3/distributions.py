"""绑定实际导入的发行包文件、版本、安装元数据与RECORD。"""
import base64
import hashlib
import importlib.metadata as metadata
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import sha, require


def record_match(path, record):
    if record.hash is None:
        return None
    digest = hashlib.new(record.hash.mode)
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    value = base64.urlsafe_b64encode(digest.digest()).decode().rstrip('=')
    require(value == record.hash.value, 'Installed RECORD mismatch: ' + str(path))
    return dict(mode=record.hash.mode, value=value, matches=True)


def package_record(distribution, records):
    artifacts = {}
    for item in records:
        if str(item).endswith(('.dist-info/METADATA', '.dist-info/RECORD', '.egg-info/PKG-INFO')):
            path = Path(distribution.locate_file(item)).resolve()
            artifacts[str(path)] = sha(path)
    require(bool(artifacts), 'Distribution lacks installed metadata')
    return dict(name=distribution.metadata['Name'], version=distribution.version, identities=artifacts,
                installation_root=str(Path(distribution.locate_file('')).resolve()))


def bind(snapshot):
    targets = {Path(name) for name, row in snapshot['files'].items() if row['category'] == 'dependency'}
    owners, packages = {}, {}
    for distribution in metadata.distributions():
        root = Path(distribution.locate_file('')).resolve()
        wanted = {str(p.relative_to(root)): p for p in targets if p.is_relative_to(root)}
        records = list(distribution.files or [])
        matches = [record for record in records if str(record) in wanted]
        if not matches:
            continue
        package = package_record(distribution, records)
        key = package['name'] + '==' + package['version'] + '@' + package['installation_root']
        packages[key] = package
        for record in matches:
            path = wanted[str(record)]
            owners[str(path)] = dict(package=key, installed_record=record_match(path, record))
    for row in snapshot['modules'].values():
        cached = row.get('cached')
        if cached in {str(p) for p in targets} and cached not in owners and row['file'] in owners:
            owners[cached] = dict(package=owners[row['file']]['package'], generated_cache_of=row['file'],
                                  installed_record=None)
    missing = sorted(str(p) for p in targets if str(p) not in owners)
    require(not missing, 'Unattributed dependency files: ' + repr(missing[:8]))
    return dict(files=owners, packages=packages)


def verify(binding):
    for package in binding['packages'].values():
        descriptor = next(name for name in package['identities'] if name.endswith(('METADATA', 'PKG-INFO')))
        installed = metadata.Distribution.at(Path(descriptor).parent)
        require(installed.version == package['version'], 'Installed version changed')
        for name, digest in package['identities'].items():
            require(sha(name) == digest, 'Distribution metadata changed: ' + name)
