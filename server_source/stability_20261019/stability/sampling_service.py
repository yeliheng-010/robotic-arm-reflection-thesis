"""记录采样解码身份的本地教师服务。"""
from http.server import HTTPServer
import json
from stability.experiment import OUT
from stability.sampling_runtime import SamplingModel
from training.refine.teacher_service import handler_class


def main():
    output = OUT/'teacher_sampling'
    output.mkdir(exist_ok=True)
    model = SamplingModel()
    parent = handler_class(model, output)

    class Handler(parent):
        def do_GET(self):
            self.reply(200, model.identity()) if self.path == '/health' else self.reply(404, {})

    with HTTPServer(('127.0.0.1', 18823), Handler) as server:
        print(json.dumps(dict(ready=True, **model.identity())), flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()

