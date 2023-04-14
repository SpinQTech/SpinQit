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
import time

import numpy as np
from .optimizer import Optimizer


class GradientDescent(Optimizer):
    def __init__(self,
                 maxiter: int = 1000,
                 tolerance: float = 1e-6,
                 learning_rate: float = 0.01,
                 verbose: bool = True, ):

        super().__init__()

        self.__maxiter = maxiter
        self.__tolerance = tolerance
        self.__learning_rate = learning_rate
        self.__verbose = verbose

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

        loss, derivative = expval_fn.backward()
        params -= derivative * self.__learning_rate
        expval_fn.update(params)
        return loss
