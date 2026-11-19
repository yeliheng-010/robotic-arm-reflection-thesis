"""独立离线审核，复用冻结审计，输出候选数据及证据清单。"""
import importlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from curation import curate, verify_export, verify_groups
from diagnostics import hard_diagnostics
from extract import transitions, split_for
from semanticfix2.protocol import sha

ROOT = Path('/home/yeliheng/grasp_server')
HERE = ROOT/'data_review_v1'
BATCHES = [('noisy_loop_v1','noisyloop'), ('scene_expansion_v1','expand'),
           ('hard_cases_v1','hardstudy')]
EXPECTED = {'noisy_loop_v1':144, 'scene_expansion_v1':200, 'hard_cases_v1':400}
TOTAL_TRANSITIONS = 635


def read_json(path):
    return json.loads(path.read_text())


def load_noisy_reader():
    path = ROOT/'noisy_loop_v1/verify.py'
    spec = importlib.util.spec_from_file_location('frozen_noisy_verify',path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_item


def audit_batch(batch, package):
    root = ROOT/batch
    protocol = importlib.import_module(package+'.protocol').verify()
    saved = read_json(root/'verification.json')
    assert saved['passed'] and saved['complete'] and saved['expected']==EXPECTED[batch]
    assert saved['protocol_sha256']==sha(root/'protocol.json') and not saved['test_used']
    reader = load_noisy_reader() if package=='noisyloop' else importlib.import_module(package+'.tasks').read
    results, groups, summaries = [], [], []
    for offset,item in enumerate(protocol['items']):
        first, second = reader(item)
        result, summary = (first,second) if package=='noisyloop' else (second,first)
        groups.append(dict(batch=batch,seed=item['seed'],split=split_for(batch,item)))
        summaries.append(summary)
        if result is not None:
            results.append(result)
        if (offset+1)%25==0:
            print(f'{batch}: audited {offset+1}/{EXPECTED[batch]}',flush=True)
    assert len(summaries)==EXPECTED[batch]
    verify_groups(groups)
    records = transitions(results,batch=batch,root=root)
    assert len(records)==saved['successful_transitions']
    evidence = dict(batch=batch,planned=len(summaries),executed=len(results),
                    skipped=len(summaries)-len(results),transitions=len(records),
                    protocol_sha256=sha(root/'protocol.json'),
                    verification_sha256=sha(root/'verification.json'),
                    transitions_sha256=sha(root/'transitions.json'))
    return records, results, evidence


def write_json(path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))


def counts(rows):
    return dict(sorted(Counter(r['split'] for r in rows).items()))


def export(directory, kept):
    exported = {}
    for split in ('train','dev','legacy_dev'):
        for source in ('combined','rule','hybrid'):
            rows = [r for r in kept if r['split']==split and
                    (source=='combined' or source in r['sources'])]
            filename = f'{split}_{source}.jsonl'
            write_jsonl(directory/filename,[dict(messages=r['messages']) for r in rows])
            write_jsonl(directory/(filename+'.index.jsonl'),
                        [{k:v for k,v in r.items() if k!='messages'} for r in rows])
            exported[filename] = len(rows)
    return exported


def finalize(records, evidence, diagnosis):
    kept, rejected = curate(records)
    verify_export(kept,rejected,records)
    directory = HERE/'output_v1'
    directory.mkdir(exist_ok=False)
    write_jsonl(directory/'provenance.jsonl',records)
    write_jsonl(directory/'quarantine.jsonl',rejected)
    write_json(directory/'hard_failures.json',diagnosis)
    exported = export(directory,kept)
    summary = dict(audit_passed=True,batches=evidence,raw_transitions=len(records),
                   raw_by_split=counts(records),unique_by_split=counts(kept),
                   dedup_removed=sum(len(r['members'])-1 for r in kept),
                   quarantine=dict(Counter(r['reason'] for r in rejected)),exports=exported,
                   groups={s:sorted({g for r in kept if r['split']==s for g in r['groups']})
                           for s in ('train','dev','legacy_dev')},
                   paired_outcomes=diagnosis['paired_outcomes'],
                   training_approved=0,training_started=False,test_used=False,
                   scope='Candidate-ID selection SFT; physical success is not optimality evidence')
    write_json(directory/'summary.json',summary)
    manifest = dict(code={p.name:sha(p) for p in sorted(HERE.glob('*.py'))},
                    artifacts={p.name:sha(p) for p in sorted(directory.iterdir()) if p.is_file()})
    write_json(directory/'manifest.json',manifest)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


def main():
    records, evidence, diagnosis = [], [], None
    for batch,package in BATCHES:
        rows, results, checked = audit_batch(batch,package)
        records.extend(rows)
        evidence.append(checked)
        if package=='hardstudy':
            diagnosis = hard_diagnostics(results)
    assert len(records)==TOTAL_TRANSITIONS
    assert sum(r['executed'] for r in evidence)==740
    assert sum(r['skipped'] for r in evidence)==4
    finalize(records,evidence,diagnosis)


if __name__=='__main__':
    main()
