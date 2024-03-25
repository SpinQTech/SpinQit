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
    import paddle
    from paddle.autograd.py_layer import PyLayer

except ImportError:
    raise ImportError(
        'You should install paddle first, use `pip install paddlepaddle` '
    )

class QuantumFunction(PyLayer):
    @staticmethod
    def forward(ctx, kwargs, *params: paddle.Tensor):
        qlayer = kwargs.get('qlayer', None)

        loss, backward_fn = qlayer.backend.get_value_and_grad_fn(qlayer.ir,
                                                                qlayer.config,
                                                                qlayer.measure_op,
                                                                qlayer.place_holder,
                                                                qlayer.grad_method)(params=params)

        # The count result return the counts directly
        # if isinstance(loss, dict):
        #     return loss

        if not isinstance(loss, dict):
            loss = paddle.to_tensor(loss, stop_gradient=False)
        ctx.backward_fn = backward_fn
        return loss

    @staticmethod
    def backward(ctx, dy):
        backward_fn = ctx.backward_fn
        gradients = backward_fn(dy.numpy())
        g_params = tuple(paddle.to_tensor(v, stop_gradient=False) for v in gradients)
        return *g_params,


def _validate_params(qlayer, params):
    if len(params) != len(qlayer.place_holder):
        raise ValueError(
            f'The number of parameter is wrong. The circuit need {len(qlayer.place_holder)} args, but got {len(params)}'
        )
    for param in params:
        if not isinstance(param, paddle.Tensor):
            raise ValueError(
                'The parameters for `paddle` interface should be paddle.Tensor'
            )


def execute(qlayer, *params):
    _validate_params(qlayer, params)
    if qlayer.backend_mode not in ['torch', 'spinq', 'jax', 'nmr', 'qasm']:
        raise ValueError(
            f'The backend_mode only support `torch`, `spinq`, `jax`, `nmr` and `qasm`, '
            f'but got backend {qlayer.backend_mode}'
        )

    kwargs = dict(
        qlayer=qlayer,
    )
    return QuantumFunction.apply(kwargs, *params)
