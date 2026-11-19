"""排查4-bit量化影响：复用现有4B权重，单卡完整FP16冻结推理。"""
from http.server import HTTPServer
import json
from stability.experiment import OUT
from stability.sampling_runtime import SamplingModel
from training.refine.runtime import MODEL_PATHS
from training.refine.teacher_service import handler_class

OUTPUT = OUT/'teacher4_full'


class FullTeacher(SamplingModel):
    def __init__(self):
        import torch
        from transformers import AutoModelForImageTextToText, AutoTokenizer
        assert torch.cuda.device_count() == 1
        torch.set_num_threads(4)
        torch.backends.cuda.enable_flash_sdp(False)
        self.path, self.architecture = MODEL_PATHS['qwen35'], 'qwen35'
        self.thinking, self.max_new_tokens = True, 4096
        self.tokenizer = AutoTokenizer.from_pretrained(self.path, local_files_only=True)
        self.model = AutoModelForImageTextToText.from_pretrained(self.path,
            local_files_only=True, torch_dtype=torch.float16,
            device_map={'': 0}, attn_implementation='eager')
        self.model.eval()

    def identity(self):
        return dict(super().identity(), precision='float16', quantization=None,
                    audit_log=str(OUTPUT/'requests.jsonl'))


def main():
    OUTPUT.mkdir(exist_ok=True)
    model = FullTeacher()
    parent = handler_class(model, OUTPUT)

    class Handler(parent):
        def do_GET(self):
            self.reply(200, model.identity()) if self.path == '/health' else self.reply(404, {})

    with HTTPServer(('127.0.0.1', 18824), Handler) as server:
        print(json.dumps(dict(ready=True, **model.identity())), flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()

