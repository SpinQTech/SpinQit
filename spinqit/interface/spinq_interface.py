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
    from autograd.extend import primitive, defvjp

except ImportError:
    raise ImportError(
        'You should install autograd first, use `pip install autograd` '
    )

import numpy as np
from spinqit.model.parameter import Parameter


def _validate_params(qlayer, params):
    if len(params) != len(qlayer.place_holder):
        raise ValueError(
            f'The length of circuits parameter is wrong. '
            f'Expected {len(qlayer.place_holder)}, but got {len(params)}. Check the parameter for qlayer or '
            f'using Circuit.add_params.'
        )
    for param in params:
        if not isinstance(param, (Parameter, np.ndarray)):
            raise ValueError(
                'The parameters for `spinq` interface should be spinqit.Parameter or np.ndarray'
            )


@primitive
def execute(qlayer, *params):
    _validate_params(qlayer, params)
    if qlayer.backend_mode not in ['torch', 'spinq', 'cloud', 'nmr', 'qasm']:
        raise ValueError(
            f'The backend_mode only support `torch`, `spinq`, `cloud`, `nmr` and `qasm`, '
            f'but got backend {qlayer.backend_mode}'
        )
    loss, backward_fn = qlayer.backend.get_value_and_grad_fn(qlayer.ir,
                                                             qlayer.config,
                                                             qlayer.measure_op,
                                                             qlayer.place_holder,
                                                             qlayer.grad_method)(params=params)
    setattr(qlayer, 'backward_fn', backward_fn)

    if not isinstance(loss, dict):
        loss = Parameter(loss)
    return loss


def execute_vjp(ans, qlayer, *params, **kwargs):
    """
    Return the grads when computing over the ir, for `spinq` interface only.

    Notice that when autograd.grad calculating the complex gradient, it should be the conjugate of g

    The following case using autograd may have some problems.

        Example:
            import autograd.numpy as anp
            from autograd import grad
            x = anp.array(2+2j)
            f = lambda x:x**2
            print('Grad :',grad(f)(x))
            ### Grad : (4+4j)

    The correct answer should be (4-4j), but we got (4+4j), so we have to use g.conj()

    Or it may cause some gradients problems
    """
    del ans, kwargs, params
    backward_fn = qlayer.backward_fn
    delattr(qlayer, 'backward_fn')

    def grad_fn(g):
        if callable(backward_fn):
            grads = backward_fn(g.conj())
        else:
            grads = backward_fn * g.conj()
        return tuple(Parameter(g) for g in grads)

    return grad_fn


defvjp(execute, execute_vjp, argnums=(1,))
