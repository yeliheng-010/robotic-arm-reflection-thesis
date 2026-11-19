"""冻结本地模型推理，显式记录架构与预算；不加载 adapter。"""
MODEL_PATHS = {
    'qwen25': '/home/yeliheng/grasp_qlora/models/Qwen2.5-7B-Instruct',
    'qwen35': '/home/yeliheng/grasp_server/qwen35/models/Qwen3.5-4B',
}


def final_answer(raw, *, thinking):
    if not thinking:
        return raw.strip()
    if '</think>' not in raw:
        raise ValueError('Thinking generation ended before final answer')
    return raw.split('</think>', 1)[1].strip()


class FrozenModel:
    def __init__(self, architecture='qwen25', *, thinking=False):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        if torch.cuda.device_count() != 1:
            raise RuntimeError('Exactly one Slurm GPU is required')
        torch.set_num_threads(4)
        torch.backends.cuda.enable_flash_sdp(False)
        self.architecture = architecture
        self.thinking = thinking
        self.max_new_tokens = 1536 if thinking else 256
        self.path = MODEL_PATHS[architecture]
        model_class = AutoModelForCausalLM
        if architecture == 'qwen35':
            from transformers import AutoModelForImageTextToText
            model_class = AutoModelForImageTextToText
        self.tokenizer = AutoTokenizer.from_pretrained(self.path, local_files_only=True)
        self.model = model_class.from_pretrained(self.path, local_files_only=True,
            torch_dtype=torch.float16, device_map={'': 0},
            attn_implementation='eager' if architecture == 'qwen35' else 'sdpa',
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16))
        self.model.eval()

    def generate(self, messages):
        import torch
        options = {'enable_thinking': self.thinking} if self.architecture == 'qwen35' else {}
        text = self.tokenizer.apply_chat_template(messages, tokenize=False,
                        add_generation_prompt=True, **options)
        inputs = self.tokenizer(text, add_special_tokens=False, return_tensors='pt').to('cuda')
        if inputs.input_ids.shape[1] > 4096:
            raise ValueError('Input exceeds the frozen token budget')
        with torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False,
                                        pad_token_id=self.tokenizer.eos_token_id)
        count = inputs.input_ids.shape[1]
        raw = self.tokenizer.decode(output[0, count:], skip_special_tokens=True)
        try:
            answer = final_answer(raw, thinking=self.thinking)
        except ValueError:
            answer = ''
        return dict(text=answer, raw_text=raw,
                    input_tokens=int(count), output_tokens=int(output.shape[1]-count),
                    model=self.path, architecture=self.architecture, adapter=None,
                    thinking=self.thinking, max_new_tokens=self.max_new_tokens)

