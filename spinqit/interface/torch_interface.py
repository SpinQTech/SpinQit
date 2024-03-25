# Copyright 2023 SpinQ Technology Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import torch
    from torch.autograd import Function
    from torch import nn
except ImportError:
    raise ImportError(
        'You should install torch first, use `pip install torch` '
    )


class QuantumFunction(Function):
    """
    The class is for constructing the Pytorch Quantum model with our own quantum circuit.
    """

    @staticmethod
    def forward(ctx, kwargs, *params: torch.Tensor, ):
        qlayer = kwargs.get('qlayer', None)
        loss, backward = qlayer.backend.get_value_and_grad_fn(qlayer.ir,
                                                              qlayer.config,
                                                              qlayer.measure_op,
                                                              qlayer.place_holder,
                                                              qlayer.grad_method)(params=params)

        ctx.torch_device = torch.device('cpu')
        for p in params:
            if p.is_cuda:
                ctx.torch_device = p.get_device()
        if not isinstance(loss, dict):
            loss = torch.as_tensor(
                loss,
                device=ctx.torch_device,
                dtype=qlayer.dtype if qlayer.dtype is not None else None,
            )

        ctx.backward = backward
        return loss

    @staticmethod
    def backward(ctx, grad_output):
        backward = ctx.backward
        gradients = backward(grad_output)
        g_params = tuple(torch.as_tensor(v, device=ctx.torch_device) for v in gradients)
        return None, *g_params,

class QuantumModule(nn.Module):
    def __init__(self, quantum_layer, weight_shape, bias=None):
        super(QuantumModule, self).__init__()
        self.w = nn.Parameter(0.01 * torch.randn(weight_shape), requires_grad=True)
        self.b = bias
        self.quantum_layer = quantum_layer

    def forward(self, state):
        res = torch.zeros(state.size(0))
        kwargs = dict(
            qlayer=self.quantum_layer,
        )
        if len(state.shape) > 1:
            for i in range(state.size(0)):
                loss = QuantumFunction.apply(kwargs, state[i], self.w)
                res[i] += loss
        else:
            res = QuantumFunction.apply(kwargs, state, self.w)
        
        if self.b is not None:
            return res + self.b
        return res

def _validate_params(qlayer, params):
    if len(params) != len(qlayer.place_holder):
        raise ValueError(
            f'The number of parameter is wrong. The circuit need {len(qlayer.place_holder)} args, but got {len(params)}'
        )
    for param in params:
        if not isinstance(param, torch.Tensor):
            raise ValueError(
                'The parameters for `torch` interface should be torch.Tensor'
            )


def execute(qlayer, *params):
    _validate_params(qlayer, params)

    if qlayer.backend_mode not in ['torch', 'spinq', 'nmr', 'cloud']:
        raise ValueError(
            f'The backend_mode only support `torch`, `spinq`, `nmr` and `cloud`, '
            f'but got backend {qlayer.backend_mode}'
        )

    kwargs = dict(
        qlayer=qlayer,
    )
    return QuantumFunction.apply(kwargs, *params)
