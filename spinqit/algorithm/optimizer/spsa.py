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
from noisyopt import minimizeSPSA
from spinqit.algorithm import Optimizer


class SPSAOptimizer(Optimizer):
    def __init__(self,
                 maxiter: int = 100,
                 verbose=False,
                 a=1.,
                 c=1.,
                 **kwargs):
        super().__init__()
        self.niter = maxiter
        self.verbose = verbose
        self.c = c
        self.a = a
        self.kwargs = kwargs

    def optimize(self, qlayer, *params):
        if len(params) > 1:
            raise ValueError(
                f'The ScipyOptimizer only support one parameter optimize, but got {len(params)} parameters. '
                f'using other type of optimizer as well.'
            )
        loss_list = []

        def callback_fn(x):
            loss = qlayer(x)
            if self.verbose and len(loss_list) % 5 == 0:
                print('Optimize: step {}, loss: {},'.format(len(loss_list) + 1, loss))
            loss_list.append(loss)

        minimizeSPSA(qlayer, *params,
                     niter=self.niter,
                     paired=False,
                     callback=callback_fn,
                     c=self.c, a=self.a, **self.kwargs)
        return loss_list
