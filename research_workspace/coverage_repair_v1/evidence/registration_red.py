"""相机登记选择器，先复现旧选择行为。"""
def configuration(cases, seed):
    return next(c['config'] for c in cases if c['item']['seed']==seed)
