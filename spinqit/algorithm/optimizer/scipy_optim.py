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
from scipy.optimize import minimize

from spinqit.algorithm.optimizer.optimizer import Optimizer


class ScipyOptimizer(Optimizer):
    def __init__(self, maxiter: int = 10000,
                 tolerance: float = 1e-4,
                 verbose=False,
                 method='COBYLA',
                 **kwargs):
        super(ScipyOptimizer, self).__init__()
        if kwargs.get('option', None):
            self.options = kwargs.get('option', None)
        else:
            self.options = {'maxiter': maxiter}
        self.verbose = verbose
        self.tol = tolerance
        self.method = method
        self.kwargs = kwargs

    def optimize(self, fn, *params):
        if len(params) > 1:
            raise ValueError(
                f'The ScipyOptimizer only support 1 parameter optimize, but got {len(params)} parameters. '
                f'using other type of optimizer as well.'
            )
        loss_list = []

        def callback_fn(x):
            loss = fn(x)
            if self.verbose and len(loss_list) % 5 == 0:
                print('Optimize: step {}, loss: {},'.format(len(loss_list) + 1, loss))
            loss_list.append(loss)

        minimize(fn, x0=params[0],
                 method=self.method, options=self.options, callback=callback_fn,
                 tol=self.tol, **self.kwargs)
        return loss_list
