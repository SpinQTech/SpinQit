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
try:
    import torch
    IMPORTED = True
except ImportError:
    IMPORTED = False
from spinqit.interface.qlayer import QLayer
from .utils import optimizer_timer
from ..optimizer import Optimizer
from ...model.parameter import Parameter
from ...utils import requires_grad

if IMPORTED:
    optim_map = {'NAdam': torch.optim.NAdam,
                 'Adam': torch.optim.Adam,
                 'SGD': torch.optim.SGD,
                 'AdamW': torch.optim.AdamW,
                 'Adagrad': torch.optim.Adagrad,
                 'RMSprop': torch.optim.RMSprop}


class TorchOptimizer(Optimizer):
    def __init__(self,
                 maxiter: int = 1000,
                 tolerance: float = 1e-6,
                 learning_rate: float = 0.01,
                 verbose: bool = True,
                 optim_type='NAdam',
                 **kwargs):
        super().__init__()

        self._optim_type = optim_type
        self.__maxiter = maxiter
        self.__tolerance = tolerance
        self._verbose = verbose
        self._step = 1
        self.__learning_rate = learning_rate
        self.__kwargs = kwargs
        self._optimizer = None

    def optimize(self, qlayer, *params):
        if not IMPORTED:
            raise ValueError(
                'To use Torch Optimizer, you should install pytorch first.'
            )
        if not isinstance(qlayer, QLayer):
            raise ValueError(
                'The qlayer parameter must be Qlayer.'
            )
        origin_interface = qlayer.interface
        qlayer.interface = 'torch'
        execute_params = self.reset(params)
        loss_list = []
        while self._step <= self.__maxiter + 1:
            loss = self.step_and_cost(qlayer, execute_params)
            if self.check_optimize_done(loss, loss_list):
                qlayer.interface = origin_interface
                break
            self._step += 1
        return loss_list

    @optimizer_timer
    def step_and_cost(self, qlayer, params):
        self._optimizer.zero_grad(set_to_none=True)
        loss = qlayer(*params)
        loss.backward()
        self._optimizer.step()
        return loss.item()

    def check_optimize_done(self, loss, loss_list):
        if loss_list and abs(loss - loss_list[-1]) < self.__tolerance:
            print(f'The loss difference less than {self.__tolerance}. Optimize done')
            check = True
        elif self._step == self.__maxiter:
            print('The optimized process has been reached the max iteration number.')
            check = True
        else:
            check = False
        loss_list.append(loss)
        return check

    def reset(self, params):
        self._step = 1

        execute_params = []
        for param in params:
            if not isinstance(param, (torch.Tensor, Parameter)):
                raise ValueError(
                    f'The params should be `torch.Tensor` or `spinqit.Parameter`, but got type{type(param)}'
                )
            _params = torch.as_tensor(param).requires_grad_(requires_grad(param))
            execute_params.append(_params)
        self._optimizer = optim_map[self._optim_type]((v for v in execute_params), lr=self.__learning_rate, **self.__kwargs)
        return execute_params
