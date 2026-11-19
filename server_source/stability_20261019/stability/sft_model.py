"""复用已验证的V100 NF4/FP16 Qwen3.5兼容设置。"""
import functools
import importlib.metadata
import os
import random
import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig


def protect_delta():
    from transformers.models.qwen3_5 import modeling_qwen3_5 as implementation

    def keep_fp32(function):
        @functools.wraps(function)
        def forward(*values, **kwargs):
            with torch.autocast('cuda', enabled=False):
                return function(*values, **kwargs)
        return forward

    for name in ('torch_chunk_gated_delta_rule', 'torch_recurrent_gated_delta_rule'):
        setattr(implementation, name, keep_fp32(getattr(implementation, name)))


def device_setup(seed):
    random.seed(seed)
    torch.manual_seed(seed)
    assert os.environ.get('SLURM_JOB_ID'), 'GPU work requires Slurm'
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1
    assert 'sm_70' in torch.cuda.get_arch_list()
    torch.cuda.set_device(0)
    torch.backends.cuda.enable_flash_sdp(False)
    protect_delta()
    return {'job': os.environ['SLURM_JOB_ID'], 'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'),
        'device': torch.cuda.get_device_name(0), 'versions': {n: importlib.metadata.version(n)
        for n in ('torch', 'transformers', 'peft', 'accelerate', 'bitsandbytes')},
        'delta_precision': 'fp32_reference_without_autocast'}


def load_model(config):
    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
        bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)
    model = AutoModelForImageTextToText.from_pretrained(config['model'], local_files_only=True,
        trust_remote_code=False, quantization_config=quantization, torch_dtype=torch.float16,
        device_map={'': 0}, attn_implementation='eager')
    assert model.is_loaded_in_4bit
    model.config.use_cache = False
    model.config.text_config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
                                            gradient_checkpointing_kwargs={'use_reentrant': False})
    target = (r'.*language_model\.layers\.\d+\.(?:self_attn|linear_attn|mlp)\.'
              r'(?:q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj|'
              r'in_proj_qkv|in_proj_z|in_proj_b|in_proj_a|out_proj)')
    model = get_peft_model(model, LoraConfig(task_type='CAUSAL_LM', r=config['rank'],
        lora_alpha=config['rank']*2, lora_dropout=.05, target_modules=target, bias='none'))
    trainable = {n: p for n, p in model.named_parameters() if p.requires_grad}
    assert trainable and all('lora_' in n for n in trainable)
    return model, trainable


def tokenizer(model_path):
    return AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)


def batch(row):
    return {k: torch.tensor([v], device='cuda') for k, v in row.items()}
