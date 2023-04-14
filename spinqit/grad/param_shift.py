# Copyright 2022 SpinQ Technology Co., Ltd.
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

import numpy as np
from autograd import grad as _grad


def parameter_shift(ir, config, params, hamiltonian, backend, state):
    grads = np.zeros_like(params, dtype=float)
    r = 0.5
    for v in ir.dag.vs:
        if 'trainable' in v.attributes():
            if not v['trainable']:
                continue
            _params = v['params']
            func = v['trainable']
            coeff = _grad(func)(params)
            v['params'] = [_params[0] + np.pi / (4 * r)]
            value1 = backend.expval(ir, config, hamiltonian, state)
            v['params'] = [_params[0] - np.pi / (4 * r)]
            value2 = backend.expval(ir, config, hamiltonian, state)
            grads += coeff * (value1 - value2) * r
            v['params'] = _params
    loss = backend.expval(ir, config, hamiltonian, state, )
    return loss, grads
