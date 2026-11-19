"""只改变输出预算，诊断被截断的碰撞开发例。"""
import json
from pathlib import Path
import smoke

path = smoke.ROOT/'collision_budget1024.json'
assert not path.exists(), 'Preserve earlier diagnostic'
smoke.MAX_NEW_TOKENS = 1024
rows, digest = smoke.development_examples()
index, row = next((i, r) for i, r in rows if r['metadata']['fault'] == 'collision')
result = smoke.reflection_example(index, row)
result.update(purpose='output_budget_diagnostic_not_same_budget_comparison',
              validation_sha256=digest, test_used=False, physics_evaluated=False)
path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps({k: result[k] for k in ('finish_reason','legal_correction','changes_exact_match','elapsed_s')}))
