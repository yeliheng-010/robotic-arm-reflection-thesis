"""冻结前静态预检；不执行物理任务，不剔除几何失败条件。"""
import ast
import json
from expand.design import ROOT,scenes,items,configuration
from expand.bridge import geometry
from stability.collection_status import atomic


def source_check():
    rows=[]
    for path in sorted(ROOT.rglob('*.py')):
        tree=ast.parse(path.read_text())
        functions=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        length=len(path.read_text().splitlines())
        longest=max([n.end_lineno-n.lineno+1 for n in functions] or [0])
        positional=max([len(n.args.args)-(1 if n.args.args and n.args.args[0].arg in ('self','cls') else 0)
                        for n in functions] or [0])
        assert length<=300 and longest<=50 and positional<=3,(path,length,longest,positional)
        rows.append(dict(path=str(path),lines=length,longest_function=longest,positional=positional))
    return rows


rows=[dict(item=item,geometry=geometry(item)) for item in scenes()]
value=dict(passed=True,scenes=len(rows),planned_tasks=len(items()),
    geometry_passed=sum(r['geometry']['passed'] for r in rows),rows=rows,source_checks=source_check())
atomic(ROOT/'preflight.json',value)
print(json.dumps({k:v for k,v in value.items() if k not in ('rows','source_checks')}))
