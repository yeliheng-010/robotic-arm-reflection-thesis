from model_grasp_gpu_v1.common import ROOT, PROJECT, SOURCE, BUDGET, read, save, sha


def main():
    prior = read(PROJECT/'coverage_repair_v1/manifest.json')
    result = read(SOURCE/'result.json')
    identities = dict(prior['identities'], **result['identities'])
    identities[str(SOURCE/'result.json')] = sha(SOURCE/'result.json')
    for name in ('ai_visual_input_v1/mm_generator.py', 'ai_diagnosis_failure_v1/f_generator.py',
                 'ai_diagnosis_failure_v1/f_response.py', 'candidate_sft_v2/manifest.json',
                 'candidate_sft_v2/runtime.py'):
        identities[str(PROJECT/name)] = sha(PROJECT/name)
    for folder in (ROOT, PROJECT/'model_grasp_intent_v1'):
        for path in folder.iterdir():
            if path.suffix in ('.py', '.sh', '.sbatch', '.md'):
                identities[str(path)] = sha(path)
    for name, digest in identities.items():
        assert sha(name) == digest, name
    save(ROOT/'manifest.json', dict(case=result['case'], source=str(SOURCE), budget=BUDGET,
         identities=identities, physical_attempts=0, training_runs=0,
         condition='F1_964347_varied_noisy', phase='frozen_observation_model_planning_replay',
         planning_timeout_s=120, model_process_timeout_s=300, adapter_enabled=False))
    print(dict(registered=True, files=len(identities), budget=BUDGET), flush=True)


if __name__ == '__main__':
    main()
