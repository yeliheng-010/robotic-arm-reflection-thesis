import os
import json
import unittest
from pathlib import Path
from transformers import AutoProcessor
from f_common import read, save, sha
from encoding import encode

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_safe_visual_loop_v1'
MODEL = ROOT.parent/'qwen35/models/Qwen3.5-4B'


def main():
    assert os.environ.get('SLURM_JOB_ID')
    tested = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT)))
    assert tested.wasSuccessful()
    source = SOURCE/'cases/A0_962905_varied_noisy/fixed_rule/result.json'
    audit = read(SOURCE/'audits/A0_962905_varied_noisy.json')
    branch = read(source)
    assert audit['passed'] and sha(source)==audit['identities'][str(source)]
    assert branch['ledger']['steps'][1]['success']
    event = branch['decisions'][0]
    assert sha(event['input_path']) == event['input_sha256']
    bundle = read(event['input_path'])
    assert all(sha(p)==h for p,h in zip(bundle['visual']['paths'],bundle['visual']['sha256']))
    messages = bundle['direct_messages']
    content = [dict(type='image',image=p) for p in bundle['visual']['paths']]
    content.append(dict(type='text',text=messages[1]['content']))
    messages = [messages[0],dict(role='user',content=content),
        dict(role='assistant',content=json.dumps(dict(action=event['action']),ensure_ascii=False))]
    processor = AutoProcessor.from_pretrained(str(MODEL),local_files_only=True,trust_remote_code=False,
        min_pixels=128*128,max_pixels=448*448)
    values, stats = encode(processor,messages)
    answer = processor.tokenizer.decode(values['input_ids'][0,stats['prompt_tokens']:],skip_special_tokens=True).strip()
    assert json.loads(answer) == dict(action=event['action'])
    paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch'), source,Path(event['input_path'])]
    save(ROOT/'encoder_verification.json',dict(passed=True,tests=tested.testsRun,stats=stats,
        training_updates=0,model_calls=0,pilot_sample_used_for_interface_check_only=True,
        identities={str(p):sha(p) for p in paths}))
    print(dict(passed=True,stats=stats,training_updates=0,model_calls=0),flush=True)


if __name__ == '__main__':
    main()
