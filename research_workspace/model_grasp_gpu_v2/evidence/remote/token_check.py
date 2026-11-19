"""使用真实processor计数，不加载权重或调用生成。"""
from transformers import AutoProcessor
from model_grasp_gpu_v1.common import PROJECT, SOURCE, read, save, verify
from model_grasp_gpu_v2.scope import ROOT, bind
from model_grasp_gpu_v2.pack import pack
from model_grasp_intent_v1.requests import messages
from mm_generator import MAX_IMAGE_PIXELS, MIN_IMAGE_PIXELS
from f_response import MAX_INPUT_TOKENS


def count(processor, request):
    prompt = messages(request)
    content = [dict(type='image',image=str(SOURCE/'execution/attempt_1/before.png')),
               dict(type='text',text=prompt[1]['content'])]
    values = processor.apply_chat_template([prompt[0],dict(role='user',content=content)],
        tokenize=True,return_dict=True,return_tensors='pt',add_generation_prompt=True,enable_thinking=False)
    return int(values['input_ids'].shape[1])


def main():
    with bind():
        verify()
    config = read(PROJECT/'candidate_sft_v2/manifest.json')
    processor = AutoProcessor.from_pretrained(config['model'],local_files_only=True,
        trust_remote_code=False,min_pixels=MIN_IMAGE_PIXELS,max_pixels=MAX_IMAGE_PIXELS)
    original = read(PROJECT/'model_grasp_gpu_v1/run/decision_1/request.json')
    compact = pack(original)
    worst = pack(original)
    action = dict(id='PROPOSE_GRASP',args=dict(region='long_negative',depth_mm=30,
                  tilt_deg=90,azimuth_deg=315,symmetry_deg=180))
    worst['history'] = [dict(revision=0,action=action,feedback=dict(status='planner_budget_exhausted'))]*3
    counts = dict(original=count(processor,original),compact=count(processor,compact),
                  max_history=count(processor,worst))
    assert counts['original'] > MAX_INPUT_TOKENS
    assert max(counts['compact'],counts['max_history']) <= MAX_INPUT_TOKENS
    save(ROOT/'token_gate.json',dict(passed=True,counts=counts,limit=MAX_INPUT_TOKENS,
                                    model_generations=0,physical_attempts=0))
    print(dict(token_gate=True,counts=counts),flush=True)


if __name__ == '__main__':
    main()
