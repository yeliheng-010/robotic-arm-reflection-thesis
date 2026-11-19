"""基于解释器真实根目录分类；所有真实导入文件均绑定哈希。"""
import site
import sys
import sysconfig
from pathlib import Path
from types import ModuleType
from qualified_closure_dynamics_v1.protocol import PROJECT, sha, require


def roots():
    paths = sysconfig.get_paths()
    prefixes = sorted({sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix})
    dependencies = [paths['purelib'], paths['platlib'], *site.getsitepackages(prefixes=prefixes)]
    if site.ENABLE_USER_SITE and site.getusersitepackages() in sys.path:
        dependencies.append(site.getusersitepackages())
    return dict(project=str(PROJECT.resolve()),
                dependency=sorted({str(Path(p).resolve()) for p in dependencies}),
                stdlib=sorted({str(Path(paths[p]).resolve()) for p in ('stdlib', 'platstdlib')}))


def category(path, boundaries):
    path = Path(path).resolve()
    if any(path.is_relative_to(Path(p)) for p in boundaries['dependency']):
        return 'dependency'
    if path.is_relative_to(Path(boundaries['project'])):
        return 'project'
    if any(path.is_relative_to(Path(p)) for p in boundaries['stdlib']):
        return 'stdlib'
    raise ValueError('Unknown source boundary: ' + str(path))


def classify(path, boundaries):
    path = Path(path).resolve()
    require(path.is_file(), 'Missing real source: ' + str(path))
    return category(path, boundaries)


def add_file(path, snapshot, *, boundaries):
    resolved = Path(path).resolve()
    key = str(resolved)
    if key not in snapshot['files']:
        snapshot['files'][key] = dict(category=classify(resolved, boundaries), sha256=sha(resolved))
    return key


def implementation(module, modules):
    candidates = [type(module).__module__]
    loader = vars(module).get('__loader__')
    if loader is not None:
        candidates.append(type(loader).__module__)
    for name in candidates:
        owner = modules.get(name)
        raw = vars(owner).get('__file__') if owner is not None else None
        if isinstance(raw, str) and Path(raw).is_file():
            return name, raw
    raise ValueError('Virtual module has no real implementation source')


def fileless(module, modules, *, boundaries, snapshot, signatures=None):
    namespace = vars(module)
    spec = namespace.get('__spec__')
    origin = getattr(spec, 'origin', None)
    if origin in ('built-in', 'frozen'):
        return dict(kind=origin)
    locations = getattr(spec, 'submodule_search_locations', None)
    if locations is not None and origin is None:
        paths = [str(Path(p).resolve()) for p in locations]
        for path in paths:
            require(Path(path).is_dir(), 'Missing namespace directory')
            category(path, boundaries)
        return dict(kind='namespace', locations=paths)
    try:
        name, source = implementation(module, modules)
    except ValueError:
        from qualified_closure_dynamics_v3 import native_sources
        signatures = native_sources.signature_index(modules) if signatures is None else signatures
        row = native_sources.resolve(module, modules, signatures)
        for source in row['implementation_files']:
            add_file(source, snapshot, boundaries=boundaries)
        return row
    resolved = add_file(source, snapshot, boundaries=boundaries)
    return dict(kind='virtual', implementation_module=name, implementation_file=resolved,
                proxy_type=type(module).__module__ + '.' + type(module).__qualname__,
                declared_file=str(namespace.get('__file__')))


def collect(modules, boundaries):
    from qualified_closure_dynamics_v3.native_sources import signature_index
    signatures = signature_index(modules)
    snapshot = dict(roots=boundaries, files={}, modules={})
    for name, module in sorted(modules.items()):
        process_alias = name in ('__main__', '__mp_main__') and module is modules.get('__main__')
        if module is None or process_alias:
            continue
        namespace = vars(module)
        raw = namespace.get('__file__')
        if isinstance(raw, str) and Path(raw).is_file():
            key = add_file(raw, snapshot, boundaries=boundaries)
            row = dict(kind='file', declared_file=raw, file=key)
            cached = namespace.get('__cached__')
            if isinstance(cached, str) and Path(cached).is_file():
                row['cached'] = add_file(cached, snapshot, boundaries=boundaries)
                row['declared_cached'] = cached
        else:
            origin = getattr(namespace.get('__spec__'), 'origin', None)
            if isinstance(raw, str) and (type(module) is ModuleType or origin not in (None, 'built-in', 'frozen')):
                raise ValueError('Missing real module file: ' + raw)
            row = fileless(module, modules, boundaries=boundaries, snapshot=snapshot, signatures=signatures)
        snapshot['modules'][name] = row
    return snapshot


def verify_files(snapshot):
    for name, row in snapshot['files'].items():
        require(classify(name, snapshot['roots']) == row['category'], 'Source category changed')
        require(sha(name) == row['sha256'], 'Source changed: ' + name)
    for row in snapshot['modules'].values():
        if row['kind'] == 'file':
            require(str(Path(row['declared_file']).resolve()) == row['file'], 'Module path redirected')
            if 'cached' in row:
                require(str(Path(row['declared_cached']).resolve()) == row['cached'], 'Cache path redirected')


def interpreter():
    executable = Path(sys.executable).resolve()
    return dict(executable=str(executable), sha256=sha(executable), version=sys.version,
                prefix=sys.prefix, base_prefix=sys.base_prefix, cache_tag=sys.implementation.cache_tag)


def verify_entrypoint(modules, allowed):
    main = modules.get('__main__')
    require(main is not None, 'Missing process entrypoint')
    raw = vars(main).get('__file__')
    require(isinstance(raw, str), 'Entrypoint has no real source')
    path = Path(raw).resolve()
    require(str(path) in allowed, 'Unregistered process entrypoint: ' + str(path))
    require(sha(path) == allowed[str(path)], 'Process entrypoint changed')
    aliases = [name for name in ('__main__', '__mp_main__') if modules.get(name) is main]
    return dict(file=str(path), sha256=allowed[str(path)], aliases=aliases)
