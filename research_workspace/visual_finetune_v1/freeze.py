from pathlib import Path
from vf_common import ROOT, runtime, job, read, save, sha, verify
from vf_gate import check_ready
import json


def lines(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main():
    job('SLURM_JOB_ID')
    export_job, audit_job = job('RECOVERY_EXPORT_JOB'), job('VISUAL_DATASET_AUDIT_JOB')
    dataset = ROOT.parent/'recovery_dataset_v1/exports'/('job_'+export_job)
    source = verify(dataset/'manifest.json')
    assert all(sha(dataset/p) == h for p, h in source['outputs'].items())
    audit_path = ROOT.parent/'visual_dataset_audit_v1/results'/('job_'+audit_job+'.json')
    audit = verify(audit_path)
    assert audit['source'] == str(dataset/'manifest.json')
    comparison = ROOT.parent/'visual_comparison_v1/prepared'/('export_'+export_job)
    verify(comparison/'manifest.json')
    report = verify(comparison/'report.json')
    evidence = check_ready(source, audit, report, lines(comparison/'private_outcomes.jsonl'))
    base = runtime.verify_manifest()
    train = lines(dataset/'train.jsonl')
    audited = [r for r in audit['records'] if r['split'] == 'train']
    assert {r['input_id'] for r in train} == {r['input_id'] for r in audited}
    longest = max(audited, key=lambda r: r['stats']['prompt_tokens']+r['stats']['answer_tokens'])
    paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md',
        dataset/'manifest.json', dataset/'train.jsonl', dataset/'dev.jsonl', audit_path,
        comparison/'manifest.json', comparison/'report.json', ROOT.parent/'visual_training_v1/vt_objective.py',
        ROOT.parent/'visual_sft_v1/encoding.py', ROOT.parent/'candidate_sft_v2/manifest.json']
    identities = dict(base['identities'])
    identities.update({str(p): sha(p) for p in paths})
    value = dict(model=base['model'], dataset=str(dataset), seed=42, rank=8, learning_rate=5e-5,
        epochs=1, accumulation=4, amp_init_scale=32, train_samples=len(train),
        longest_train_input=longest['input_id'], training_authorized=True, test_used=False,
        learnable_evidence=evidence, identities=identities, scope='controlled_multimodal_action_trial')
    save(ROOT/'manifest.json', value)
    print(dict(frozen=True, samples=len(train), evidence=evidence), flush=True)


if __name__ == '__main__':
    main()
