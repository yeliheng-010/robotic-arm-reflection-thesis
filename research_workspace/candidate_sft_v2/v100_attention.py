"""显式重复KV，避免PyTorch2.6 GQA回退到高显存math SDPA。"""
import torch
from torch.nn.attention import SDPBackend,sdpa_kernel


def install():
    from transformers.integrations import sdpa_attention
    sdpa_attention.use_gqa_in_sdpa = lambda *args,**kwargs: False
    torch.backends.cuda.enable_flash_sdp(False)
    torch.backends.cuda.enable_math_sdp(False)
    torch.backends.cuda.enable_mem_efficient_sdp(True)
    torch.backends.cuda.enable_cudnn_sdp(False)


def kernel_probe():
    torch.manual_seed(42)
    q = torch.randn(1,16,128,256,device='cuda',dtype=torch.float16,requires_grad=True)
    k = torch.randn(1,4,128,256,device='cuda',dtype=torch.float16,requires_grad=True)
    v = torch.randn_like(k,requires_grad=True)
    with sdpa_kernel(SDPBackend.MATH):
        expected = torch.nn.functional.scaled_dot_product_attention(q,k,v,is_causal=True,enable_gqa=True)
        reference = torch.autograd.grad(expected.float().square().mean(),(q,k,v))
    with sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION):
        actual = torch.nn.functional.scaled_dot_product_attention(q,k.repeat_interleave(4,dim=1),
                   v.repeat_interleave(4,dim=1),is_causal=True)
        gradients = torch.autograd.grad(actual.float().square().mean(),(q,k,v))
    torch.testing.assert_close(expected,actual,atol=2e-3,rtol=1e-2)
    for a,b in zip(reference,gradients):
        torch.testing.assert_close(a,b,atol=2e-5,rtol=1e-2)
    return dict(passed=True,backend='EFFICIENT_ATTENTION',
                output_max_error=float((expected-actual).abs().max()),
                gradient_max_errors=[float((a-b).abs().max()) for a,b in zip(reference,gradients)])
