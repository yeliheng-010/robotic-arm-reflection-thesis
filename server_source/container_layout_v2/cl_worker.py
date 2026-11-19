"""单条件独立进程，无故障一次执行；失败保留在完整分母中。"""
import argparse
import json
import os
from contextlib import contextmanager, ExitStack
from unittest.mock import patch
import numpy as np
from loopstudy import episode, audit
from loopstudy.actions import initial
from recovery.references import collision_context
from cl_common import read, save, sha, verify, task
from cl_design import ROOT, CONTAINERS, configuration
from cl_geometry import verify_compiled


@contextmanager
def bound(item, layout):
    def config(current):
        return configuration(current, layout)
    def context(current, trace):
        return collision_context(dict(current, enabled=False), trace)
    with ExitStack() as stack:
        stack.enter_context(patch.object(episode, 'configuration', config))
        stack.enter_context(patch.object(audit, 'configuration', config))
        stack.enter_context(patch.object(episode, 'collision_context', context))
        yield


def audit_row(row, plan):
    item, layout = task(row['index'], plan)
    assert row['item']==item and row['test_used'] is False and row['training_approved'] is False
    if not layout['accepted'] and item['arm']=='randomized':
        assert row['status']=='geometry_rejected' and row['step'] is None
        return
    checked = verify_compiled(item, layout, plan['geometry'])
    assert row['geometry']==checked and checked['checks']['passed']
    step = row['step']
    assert step['index']==1 and step['state']==initial()
    record = read(step['result_path'])['records'][0]
    with bound(item, layout):
        audit.physical(step, item, record)
    actual = record['candidate_trace']['initial_body_xyz']
    for name in CONTAINERS:
        np.testing.assert_allclose(checked['positions'][name],
            actual[checked['body_ids'][name]][:2], atol=1e-8, rtol=0)
    assert row['success']==step['success'] and row['status']=='executed'
    assert row['error_type']==((record['error'] or {}).get('error_type'))
    assert row['images'] and any(p.endswith('before.png') for p in row['images'])
    for path, digest in row['images'].items():
        assert sha(path)==digest


def main(index):
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    plan = verify()
    item, layout = task(index, plan)
    directory = ROOT/'runs'/item['id']
    directory.mkdir(parents=True, exist_ok=False)
    row = dict(index=index, item=item, status='geometry_rejected', step=None,
               success=None, test_used=False, training_approved=False)
    if layout['accepted'] or item['arm']=='original':
        checked = verify_compiled(item, layout, plan['geometry'])
        assert checked['checks']['passed'], checked
        with bound(item, layout):
            step = episode.attempt(item, initial(), directory=directory/'attempt_1', index=1)
        record = read(step['result_path'])['records'][0]
        row.update(status='executed', geometry=checked, step=step, success=step['success'],
            error_type=(record['error'] or {}).get('error_type'),
            images={str(p):sha(p) for p in directory.rglob('*.png')})
    save(directory/'result.json', row)
    audit_row(row, plan)
    save(directory/'summary.json', dict(passed=True, **row))


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('index', type=int)
    main(parser.parse_args().index)
