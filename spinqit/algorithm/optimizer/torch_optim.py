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
import torch
from ..torch_interface import QuantumModel

from spinqit.algorithm.expval import ExpvalCost
from ..optimizer import Optimizer

optim_map = {'NAdam': torch.optim.NAdam,
             'Adam': torch.optim.Adam,
             'SGD': torch.optim.SGD,
             'AdamW': torch.optim.AdamW,
             'Adagrad': torch.optim.Adagrad}


class TorchOptimizer(Optimizer):
    def __init__(self,
                 maxiter: int = 1000,
                 tolerance: float = 1e-6,
                 learning_rate: float = 0.01,
                 verbose: bool = True,
                 optim_type='NAdam',
                 *args, **kwargs):
        super().__init__()

        self.optim_type = optim_type
        self.__maxiter = maxiter
        self.__tolerance = tolerance
        self.__verbose = verbose
        self.__learning_rate = learning_rate
        self.__args = args
        self.__kwargs = kwargs
        self.model = None
        self.optimizer = None

    def set_model(self, model):
        if isinstance(model, ExpvalCost):
            model = QuantumModel(model)
        elif isinstance(model, torch.nn.Module):
            model = model
        else:
            raise NotImplementedError(f'The model type `{type(model)}` are not supported')
        optimizer = optim_map[self.optim_type]
        optimizer = optimizer(model.parameters(), lr=self.__learning_rate, *self.__args, **self.__kwargs)
        self.model = model
        self.optimizer = optimizer

    def optimize(self, model):
        self.set_model(model)
        loss_list = []
        for step in range(1, self.__maxiter + 1):
            start = time.time()
            loss = self.step()
            end = time.time()
            if self.__verbose:
                print('Optimize: step {}, loss: {}, time: {}s'.format(step, loss, end - start))
            if loss_list and np.abs(loss - loss_list[-1]) < self.__tolerance:
                if self.__verbose:
                    print(f'The loss difference less than {self.__tolerance}. Optimize done')
                break
            loss_list.append(loss)
        return loss_list

    def step(self, ):
        self.optimizer.zero_grad(set_to_none=True)
        loss = self.model()
        loss.backward()
        self.optimizer.step()
        return loss.item()
