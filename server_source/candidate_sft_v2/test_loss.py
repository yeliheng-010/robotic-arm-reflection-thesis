"""后缀监督必须与完整因果masked loss及梯度一致。"""
import unittest
from types import SimpleNamespace
import torch
from loss import suffix_loss


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = torch.nn.Embedding(11,7)
        self.head = torch.nn.Linear(7,11,bias=False)

    def forward(self,input_ids,attention_mask,logits_to_keep=0):
        hidden = self.embedding(input_ids)
        selected = hidden[:,-logits_to_keep:,:] if logits_to_keep else hidden
        return SimpleNamespace(logits=self.head(selected))


class SuffixLossTests(unittest.TestCase):
    def test_loss_and_gradients_equal_full_sequence(self):
        torch.manual_seed(42)
        model = TinyModel()
        row = dict(input_ids=[1,2,3,4,5,6],attention_mask=[1]*6,labels=[-100]*3+[4,5,6])
        ids = torch.tensor([row['input_ids']])
        logits = model(ids,torch.ones_like(ids)).logits
        expected = torch.nn.functional.cross_entropy(logits[:,:-1].reshape(-1,11),
                                                     torch.tensor(row['labels'][1:]))
        expected.backward()
        gradients = [p.grad.clone() for p in model.parameters()]
        model.zero_grad()
        actual = suffix_loss(model,row,device='cpu')
        actual.backward()
        torch.testing.assert_close(expected.detach(),actual.detach())
        for prior,param in zip(gradients,model.parameters()):
            torch.testing.assert_close(prior,param.grad)

    def test_no_supervision_rejected(self):
        row = dict(input_ids=[1,2],attention_mask=[1,1],labels=[-100,-100])
        with self.assertRaises(ValueError):
            suffix_loss(TinyModel(),row,device='cpu')

    def test_noncontiguous_supervision_rejected(self):
        row = dict(input_ids=[1,2,3],attention_mask=[1]*3,labels=[-100,2,-100])
        with self.assertRaises(ValueError):
            suffix_loss(TinyModel(),row,device='cpu')


if __name__=='__main__':
    unittest.main()
