"""仅计算assistant后缀的因果logits，完整保留输入上下文。"""
import torch


def supervised_start(row):
    labels = row['labels']
    positions = [i for i,value in enumerate(labels) if value!=-100]
    if not positions or positions[0]==0 or positions!=list(range(positions[0],len(labels))):
        raise ValueError('Expected nonempty contiguous supervised suffix after prompt')
    if labels[positions[0]:]!=row['input_ids'][positions[0]:]:
        raise ValueError('Supervised labels must match assistant tokens')
    return positions[0]


def suffix_loss(model,row,*,device='cuda'):
    start = supervised_start(row)
    answer_size = len(row['labels'])-start
    inputs = {k:torch.tensor([row[k]],device=device) for k in ('input_ids','attention_mask')}
    logits = model(**inputs,logits_to_keep=answer_size+1).logits[:,:-1,:]
    targets = torch.tensor(row['labels'][start:],device=device)
    return torch.nn.functional.cross_entropy(logits.float().reshape(-1,logits.shape[-1]),targets)
