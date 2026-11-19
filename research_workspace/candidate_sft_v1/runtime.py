"""统一模型加载、更新及逐样本评价，训练前后共享同一路径。"""
import json
import math
from contextlib import nullcontext
from pathlib import Path
import torch
from stability.sft_model import device_setup,load_model,tokenizer
from data import ROOT,MODEL,read,sha
from loss import suffix_loss,supervised_start


def verify_manifest():
    config = read(ROOT/'manifest.json')
    for path,expected in config['identities'].items():
        assert sha(path)==expected, 'Frozen identity changed: '+path
    assert config['epochs']==1 and config['train_samples']==159
    return config


def setup(config, *, adapter=None):
    environment = device_setup(config['seed'])
    model,params = load_model(config)
    model.set_attn_implementation('sdpa')
    assert model.get_base_model().config.text_config._attn_implementation=='sdpa'
    environment['full_attention'] = 'SDPA; flash disabled on V100'
    if adapter:
        model.load_adapter(str(adapter),adapter_name='trained',is_trainable=False)
        model.set_adapter('trained')
    tok = tokenizer(str(MODEL))
    return model,params,tok,environment


def optimizer_step(model,params,*,rows,optimizer,scaler):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    sizes = [len(r['labels'])-supervised_start(r) for r in rows]
    total,measured = sum(sizes),0.0
    for row,size in zip(rows,sizes):
        with torch.autocast('cuda',dtype=torch.float16):
            loss = suffix_loss(model,row)
        value = float(loss.detach())
        assert math.isfinite(value), 'Nonfinite loss'
        measured += value*size/total
        scaler.scale(loss*size/total).backward()
    scaler.unscale_(optimizer)
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in params.values())
    norm = float(torch.nn.utils.clip_grad_norm_(list(params.values()),1.0))
    assert math.isfinite(norm) and norm>0
    previous = scaler.get_scale()
    scaler.step(optimizer)
    scaler.update()
    assert scaler.get_scale()>=previous, 'AMP skipped update'
    torch.cuda.synchronize()
    optimizer.zero_grad(set_to_none=True)
    return dict(loss=measured,gradient_norm=norm,samples=len(rows),supervised_tokens=total)


def validate_text(text, messages):
    candidates = json.loads(messages[1]['content'])['candidates']
    def unique(pairs):
        value = {}
        for key,item in pairs:
            if key in value:
                raise ValueError('Duplicate JSON key')
            value[key] = item
        return value
    try:
        value = json.loads(text,object_pairs_hook=unique)
        valid = isinstance(value,dict) and set(value)=={'action_id'}
        valid = valid and isinstance(value['action_id'],str)
        legal = valid and sum(c['id']==value['action_id'] for c in candidates)==1
        target = json.loads(messages[-1]['content'])
        return dict(json_valid=bool(valid),candidate_valid=bool(legal),
                    target_match=bool(legal and value==target))
    except (ValueError,TypeError):
        return dict(json_valid=False,candidate_valid=False,target_match=False)


def predict(model,tok,row,*,raw,baseline=False):
    model.eval()
    start = supervised_start(row)
    ids = torch.tensor([row['input_ids'][:start]],device='cuda')
    context = model.disable_adapter() if baseline else nullcontext()
    with context,torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
        loss = float(suffix_loss(model,row))
        output = model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),
            max_new_tokens=128,do_sample=False,use_cache=True,logits_to_keep=1,
            pad_token_id=tok.pad_token_id)
    assert math.isfinite(loss)
    text = tok.decode(output[0,start:],skip_special_tokens=True)
    return dict(text=text,loss=loss,supervised_tokens=len(row['labels'])-start,
                output_tokens=len(output[0])-start,**validate_text(text,raw['messages']))
