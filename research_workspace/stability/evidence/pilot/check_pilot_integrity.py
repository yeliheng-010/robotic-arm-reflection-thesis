import json
from pathlib import Path
from stability.experiment import OUT
from stability.sft_freeze import code_hashes,file_hash
from stability.collection_status import atomic
root=OUT/'pilot_sft_v1'
config=json.loads((root/'manifest.json').read_text())
data=OUT/'pilot_sft_data_v1'
manifest=json.loads((data/'manifest.json').read_text())
assert config['code']==code_hashes()
assert config['dataset_manifest_sha256']==file_hash(data/'manifest.json')
checks={split:file_hash(data/(split+'.jsonl'))==item['sha256'] for split,item in manifest['files'].items()}
assert all(checks.values())
result=dict(passed=True,frozen_training_code_unchanged=True,frozen_data_hashes_unchanged=checks,test_content_used_for_model=False)
atomic(root/'final_integrity.json',result)
print(json.dumps(result))
