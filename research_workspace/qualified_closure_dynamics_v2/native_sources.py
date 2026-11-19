"""追溯无文件原生子模块；Cython仅声称绑定签名匹配候选集合。"""
import re
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import require

CHUNK_SIZE = 1024 * 1024


def extension_path(module):
    raw = vars(module).get('__file__') if module is not None else None
    if isinstance(raw, str) and any(raw.endswith(suffix) for suffix in EXTENSION_SUFFIXES):
        path = Path(raw).resolve()
        require(path.is_file(), 'Missing native extension: ' + str(path))
        return str(path)
    return None


def helper_name(name):
    return name == 'cython_runtime' or bool(re.fullmatch(r'_cython_\d+_\d+_\d+', name))


def signature_index(modules):
    names = {vars(m).get('__name__', '') for m in modules.values() if m is not None}
    signatures = {name: name.encode() for name in names if helper_name(name)}
    result = {name: [] for name in signatures}
    if not signatures:
        return result
    paths = {extension_path(m) for m in modules.values() if m is not None}
    overlap = max(map(len, signatures.values()))
    for path in sorted(paths - {None}):
        found, tail = set(), b''
        with Path(path).open('rb') as stream:
            for block in iter(lambda: stream.read(CHUNK_SIZE), b''):
                chunk = tail + block
                found.update(name for name, token in signatures.items() if token in chunk)
                tail = chunk[-overlap:]
        for name in found:
            result[name].append(path)
    return result


def method_sources(module):
    paths = set()
    for value in vars(type(module)).values():
        code = getattr(value, '__code__', None)
        if code is not None and Path(code.co_filename).is_file():
            paths.add(str(Path(code.co_filename).resolve()))
    return sorted(paths)


def resolve(module, modules, signatures):
    methods = method_sources(module)
    canonical = vars(module).get('__name__', '')
    if methods:
        return dict(kind='virtual_class', implementation_files=methods)
    pieces = canonical.split('.')
    for end in range(len(pieces) - 1, 0, -1):
        parent_name = '.'.join(pieces[:end])
        parent = modules.get(parent_name)
        native = vars(parent).get('_native') if parent is not None else None
        path = extension_path(parent) or extension_path(native)
        if path:
            return dict(kind='native_child', canonical_name=canonical,
                        implementation_module=parent_name, implementation_files=[path])
    candidates = signatures.get(canonical, [])
    require(bool(candidates), 'Unresolved virtual module: ' + canonical)
    return dict(kind='cython_support_candidate_set', canonical_name=canonical,
                implementation_files=candidates, exact_producer_identified=False)
