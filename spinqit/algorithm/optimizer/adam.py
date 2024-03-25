# Copyright 2021 SpinQ Technology Co., Ltd.
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

from .optimizer import Optimizer
from .utils import optimizer_timer
from ...grad import qgrad


class ADAM(Optimizer):
    def __init__(self,
                 maxiter: int = 1000,
                 tolerance: float = 1e-4,
                 learning_rate: float = 0.01,
                 beta1: float = 0.9,
                 beta2: float = 0.99,
                 noise_factor: float = 1e-8,
                 verbose: bool = True, ):

        super().__init__()

        self.__vt = None
        self.__mt = None
        self.__maxiter = maxiter
        self.__tolerance = tolerance
        self.__learning_rate = learning_rate
        self.__beta1 = beta1
        self.__beta2 = beta2
        self.__noise_factor = noise_factor
        self._verbose = verbose
        self._step = 1

    def optimize(self, qlayer, *params):
        loss_list = []
        params = list(params)
        self.reset(params)
        while self._step <= self.__maxiter:
            loss = self.step_and_cost(qlayer, params)
            if self.check_optimize_done(loss, loss_list):
                break
            self._step += 1
        return loss_list

    @optimizer_timer
    def step_and_cost(self, qlayer, params):
        grad_fn = qgrad(qlayer)
        derivative = grad_fn(*params)
        loss = grad_fn.forward        
        for i in range(len(params)):
            self.__mt[i] = self.__beta1 * self.__mt[i] + (1 - self.__beta1) * derivative[i]
            self.__vt[i] = self.__beta2 * self.__vt[i] + (1 - self.__beta2) * derivative[i] * derivative[i]
            rate_eff = self.__learning_rate * np.sqrt(1 - self.__beta2 ** self._step) / (1 - self.__beta1 ** self._step)
            params[i] -= rate_eff * self.__mt[i] / (np.sqrt(self.__vt[i]) + self.__noise_factor)
        return loss

    def check_optimize_done(self, loss, loss_list):
        if loss_list and np.abs(loss - loss_list[-1]) < self.__tolerance:
            print(f'The loss difference less than {self.__tolerance}. Optimize done')
            check = True
        else:
            if self._step == self.__maxiter:
                print('The optimized process has been reached the max iteration number.')
            check = False
        loss_list.append(loss)
        return check

    def reset(self, params):
        self._step = 1
        self.__mt = [0]*len(params)
        self.__vt = [0]*len(params)
