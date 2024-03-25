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
from autograd import elementwise_grad as egrad
from spinqit.utils.function import requires_grad

def parameter_shift(ir, params, config, backend, measure_op):

    def backward_fn(dy):
        if measure_op.mtype == 'state':
            raise ValueError('The `param_shift` grad method does not support measurement of state')
        if measure_op.mtype == 'count':
            raise ValueError('The measurement of count does not support gradients calculated')

        if not dy.shape:
            dy = dy.reshape(-1)

        grads = []
        for param in params:
            grads.append(np.zeros_like(param, dtype=param.dtype))

        r = 0.5
        for v in ir.dag.vs:
            if 'func' in v.attributes() and v['func'] is not None:
                func = v['func']
                origin_param = [x for x in v['params']]
                for i in range(len(origin_param)):
                    if callable(func[i]) and requires_grad(origin_param[i]):
                        coeffs = egrad(func[i])(params)
                        v['params'][i] = origin_param[i] + np.pi / (4 * r)
                        value1, _ = backend.evaluate(ir, config, measure_op)
                        v['params'][i] = origin_param[i] - np.pi / (4 * r)
                        value2, _ = backend.evaluate(ir, config, measure_op)
                        v['params'][i] = origin_param[i]
                        g = (value1 - value2)
                        if np.allclose(g, 0):
                            continue
                        if not g.shape:
                            g = g.reshape(-1)

                        for idx, coeff in enumerate(coeffs):
                            if np.allclose(coeff, 0):
                                continue
                            grads[idx] += r * coeff * (
                                np.tensordot(g.real, dy.real, axes=[[0], [0]])
                            )
        return grads

    return backward_fn