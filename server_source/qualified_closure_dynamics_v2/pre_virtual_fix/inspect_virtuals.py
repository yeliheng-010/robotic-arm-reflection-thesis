"""只读列出实际导入中的无文件模块及可追溯实现线索。"""
import os
import sys
from pathlib import Path
from qualified_closure_dynamics_v2.protocol import ROOT, save, require
from qualified_closure_dynamics_v2 import provenance
from qualified_closure_dynamics_v2.guarded_imports import zero_motion, load_runtime


def describe(name, module, modules):
    data = vars(module)
    ancestors = []
    pieces = name.split('.')
    for end in range(len(pieces) - 1, 0, -1):
        parent = '.'.join(pieces[:end])
        obj = modules.get(parent)
        if obj is not None:
            attrs = vars(obj)
            native = attrs.get('_native')
            ancestors.append(dict(name=parent, file=attrs.get('__file__'),
                native_file=vars(native).get('__file__') if native is not None else None))
    return dict(name=name, type=type(module).__module__ + '.' + type(module).__qualname__,
                file=data.get('__file__'), origin=getattr(data.get('__spec__'), 'origin', None),
                loader_type=str(type(data.get('__loader__'))),
                doc=str(data.get('__doc__'))[:180], ancestors=ancestors)


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    with zero_motion() as counts:
        load_runtime()
        modules = dict(sys.modules)
        roots = provenance.roots()
        unresolved, extensions = [], []
        for name, module in sorted(modules.items()):
            if module is None or name == '__main__':
                continue
            raw = vars(module).get('__file__')
            if isinstance(raw, str) and Path(raw).is_file():
                if raw.endswith('.so'):
                    extensions.append(dict(name=name, path=raw))
                continue
            try:
                provenance.fileless(module, modules, boundaries=roots, snapshot=dict(files={}))
            except ValueError:
                unresolved.append(describe(name, module, modules))
        require(not any(counts.values()), 'Attempted simulation')
    save(ROOT / 'virtual_diagnostic.json', dict(unresolved=unresolved, extensions=extensions,
         counts=counts, job=os.environ['SLURM_JOB_ID']))
    print(dict(unresolved=len(unresolved), names=[r['name'] for r in unresolved][:25], counts=counts), flush=True)


if __name__ == '__main__':
    main()
