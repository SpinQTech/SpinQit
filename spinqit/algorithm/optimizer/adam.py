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
import time

import numpy as np

from .optimizer import Optimizer


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
        self.__verbose = verbose
        self.__accumulation = 1

    def optimize(self, expval_fn):
        params = expval_fn.params
        loss_list = []
        for step in range(1, self.__maxiter + 1):
            start = time.time()
            loss = self.step(expval_fn, params)
            end = time.time()
            if self.__verbose:
                print('Optimize: step {}, loss: {}, time: {}s'.format(step, loss, end - start))
            if loss_list and np.abs(loss - loss_list[-1]) < self.__tolerance:
                if self.__verbose:
                    print(f'The loss difference less than {self.__tolerance}. Optimize done')
                break
            loss_list.append(loss)
        return loss_list

    def step(self, expval_fn, params):

        if self.__mt is None:
            self.__mt = np.zeros_like(params)

        if self.__vt is None:
            self.__vt = np.zeros_like(params)

        loss, derivative = expval_fn.backward()
        self.__mt = self.__beta1 * self.__mt + (1 - self.__beta1) * derivative
        self.__vt = self.__beta2 * self.__vt + (1 - self.__beta2) * derivative * derivative
        rate_eff = self.__learning_rate * np.sqrt(1 - self.__beta2 ** self.__accumulation) / (1 - self.__beta1 ** self.__accumulation)
        params -= rate_eff * self.__mt / (np.sqrt(self.__vt) + self.__noise_factor)
        self.__accumulation += 1
        expval_fn.update(params)
        return loss
