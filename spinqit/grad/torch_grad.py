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
    IMPORTED = True
except ImportError:
    IMPORTED = False
from autograd import elementwise_grad as egrad

from spinqit import Parameter
from spinqit.utils.function import requires_grad


def grad_func(ir, params, config, backend, measure_op, res, grad_method):
    if not IMPORTED:
        raise ImportError(
            'torch has not install, use `pip install torch`'
        )
    if grad_method == 'backprop':
        backward_fn = backprop(res, params, measure_op)
    elif grad_method == 'param_shift':
        backward_fn = parameter_shift(ir, params, config, backend, measure_op)
    else:
        def backward_fn(*args):
            raise ValueError(
                f'The grad_method {grad_method} is not supported for `torch` backend now'
            )
    return backward_fn


def backprop(val, params_for_grad, measure_op):

    def backward_fn(dy):
        if measure_op.mtype in ['count']:
            raise ValueError('The measurement of count does not support gradients calculated')

        dy = torch.as_tensor(dy)
        val.backward(dy)
        grads = []
        for v in params_for_grad:
            if v.grad is not None:
                grads.append(v.grad.cpu().detach().numpy())
                v.grad = None
            else:
                grads.append(torch.zeros_like(v).numpy())
        return grads

    return backward_fn


def parameter_shift(ir, params, config, backend, measure_op):
    def backward_fn(dy):
        if measure_op.mtype == 'state':
            raise ValueError('The `param_shift` grad method does not support measurement of state')
        if measure_op.mtype == 'count':
            raise ValueError('The measurement of count does not support gradients calculated')
        if not dy.shape:
            dy = dy.reshape(-1)
        dy = torch.as_tensor(dy)
        grads = []
        for param in params:
            grads.append(torch.zeros_like(param, dtype=param.dtype))
        params_for_grad = [Parameter(p.cpu().detach()) for p in params]
        r = 0.5
        with torch.no_grad():
            for v in ir.dag.vs:
                if 'func' in v.attributes() and v['func'] is not None:
                    func = v['func']
                    origin_param = [x for x in v['params']]
                    for i in range(len(origin_param)):
                        if callable(func[i]) and requires_grad(origin_param[i]):
                            v['params'][i] = origin_param[i] + torch.pi / (4 * r)
                            value1, _ = backend.evaluate(ir, config, measure_op)
                            v['params'][i] = origin_param[i] - torch.pi / (4 * r)
                            value2, _ = backend.evaluate(ir, config, measure_op)
                            v['params'][i] = origin_param[i]
                            g = (value1 - value2)
                            coeffs = [torch.as_tensor(x, dtype=g.dtype) for x in (egrad(func[i])(params_for_grad))]
                            if torch.allclose(g, torch.tensor(0., dtype=g.dtype)):
                                continue
                            if not g.shape:
                                g = g.reshape(-1)

                            for idx, coeff in enumerate(coeffs):
                                if torch.allclose(coeff, torch.tensor(0., dtype=g.dtype)):
                                    continue
                                grads[idx] += r * coeff * (
                                    torch.tensordot(g.real, dy.real, dims=[[0], [0]])
                                )
            return [g.cpu().numpy() for g in grads]

    return backward_fn
