"""先核验冻结来源，再排他消费一次执行预算。"""
from cc_common import read, save, sha, verify


def claim(trial):
    manifest = verify(trial/'manifest.json')
    execution = verify(trial/'execution_manifest.json')
    assert manifest['max_attempts'] == execution['max_physical_attempts'] == 1
    assert read(trial/'preflight_result.json')['passed']
    assert not (trial/'cases').exists(), 'Existing attempt must not be repeated'
    save(trial/'attempt_claim.json', dict(physical_attempt_budget_consumed=1,
        manifest_sha256=sha(trial/'manifest.json'),
        execution_manifest_sha256=sha(trial/'execution_manifest.json')))
