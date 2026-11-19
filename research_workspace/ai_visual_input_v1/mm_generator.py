from transformers import AutoProcessor
from f_generator import Generator
from f_response import MAX_INPUT_TOKENS

MAX_IMAGE_PIXELS = 448*448
MIN_IMAGE_PIXELS = 128*128


class VisualGenerator(Generator):
    def __init__(self):
        super().__init__()
        self.processor = AutoProcessor.from_pretrained(self.identity['model_path'], local_files_only=True,
            trust_remote_code=False, min_pixels=MIN_IMAGE_PIXELS, max_pixels=MAX_IMAGE_PIXELS)

    def prepare_images(self, messages, paths):
        assert [row['role'] for row in messages] == ['system', 'user'] and 1 <= len(paths) <= 2
        content = [dict(type='image', image=path) for path in paths]
        content.append(dict(type='text', text=messages[1]['content']))
        multimodal = [messages[0], dict(role='user', content=content)]
        values = self.processor.apply_chat_template(multimodal, tokenize=True, return_dict=True,
            return_tensors='pt', add_generation_prompt=True, enable_thinking=False).to('cuda')
        assert values['input_ids'].shape[1] <= MAX_INPUT_TOKENS
        assert 'pixel_values' in values and 'image_grid_thw' in values
        return values, dict(pixel_values_shape=list(values['pixel_values'].shape),
            image_grid_thw=values['image_grid_thw'].cpu().tolist(), input_tokens=values['input_ids'].shape[1])
