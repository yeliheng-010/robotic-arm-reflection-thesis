"""生成停止条件以实际generation_config为准，不猜测tokenizer默认EOS。"""
def finish_reason(last_token,*,eos_ids,generated,budget):
    eos={eos_ids} if isinstance(eos_ids,int) else set(eos_ids or [])
    if last_token in eos:
        return 'stop'
    if generated>=budget:
        return 'length'
    raise ValueError('Generation stopped before budget without a configured EOS')
