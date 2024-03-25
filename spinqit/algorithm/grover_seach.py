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

import math
import random

import numpy as np

from spinqit import Circuit, H, X, Z
from spinqit import get_compiler
from spinqit.backend import check_backend_and_config
from spinqit.primitive import MultiControlledGateBuilder


class QSearching:
    """
    Using Grover algorithm to find the maximum or minimum value of an unstructured dataset

    Args:
        find: Define searching whether minimum or maximum value
    """

    def __init__(self, objective:str ='max', backend_mode:str ='spinq', seed=None, **kwargs):
        self.__find = objective
        self.__backend, self.__config = check_backend_and_config(backend_mode, **kwargs)
        self.__seed = seed
        self.__compiler = get_compiler('native')

    def search(self, dataset, show=True) -> int:
        if not self._is_power2(len(dataset)):
            raise ValueError("The size of the dataset must be a power of 2!")
        if self.__find == 'max':
            max_index = self._search(dataset)
            if show:
                if max_index is None:
                    print("= The algorithm fails to find the maximum element and its index")
                else:
                    print("= The maximum element is: {}".format(dataset[max_index]))
                    print("= The index of the maximum element is: {}".format(max_index))
            return max_index
        elif self.__find == 'min':
            min_index = self._search(dataset)
            if show:
                if min_index is None:
                    print("= The algorithm fails to find the minimum element and its index")
                else:
                    print("= The minimum element is: {}".format(dataset[min_index]))
                    print("= The index of the minimum element is: {}".format(min_index))
            return min_index

    def _search(self, dataset) -> int:
        if self.__seed is not None:
            random.seed(self.__seed)
        else:
            random.seed(len(dataset))
        index = random.randint(0, len(dataset) - 1)
        i = 0
        while i <= math.ceil(math.log(len(dataset), 2))+1:
            new_index = self.__run_grover(dataset, dataset[index])
            if new_index != 'No answer':
                index = new_index
                i += 1
            else:
                i += 0.5
        return index

    def __run_grover(self, dataset, threshold=None):
        N = len(dataset)
        n = math.ceil(math.log2(N))

        # number of maximum iterations we may run
        num_it = int(9 / 4 * np.sqrt(N))

        m = 1
        lam = 6 / 5

        for j in range(num_it):
            grover_iter = random.randint(0, int(m))
            circ = Circuit()
            q = circ.allocateQubits(n)

            # superposition state
            for i in q:
                circ << (H, [i])

            # allocate the oracle working qubit
            oracle_q = circ.allocateQubits(1)
            circ << (X, oracle_q)
            circ << (H, oracle_q)

            # Apply the grover operator on the circuit
            for _ in range(grover_iter):
                self.__grover_operator(circ, dataset, threshold, oracle_q, q, )
            
            exe = self.__compiler.compile(circ, 0)
            self.__config.configure_measure_qubits(q)
            result = self.__backend.execute(exe, self.__config)

            index = np.inf
            # According to the result, choose next index
            while index >= len(dataset):
                index = int(result.get_random_reading()[::-1], 2)
            if self.__find == 'max':
                if dataset[index] > threshold:
                    return index
            elif self.__find == 'min':
                if dataset[index] < threshold:
                    return index
            m *= lam
        return 'No answer'

    def __grover_operator(self, circ, dataset, threshold, oracle_q, q, ):
        n = len(q)
        self.__build_oracle(circ, dataset, threshold, oracle_q, q, )
        for i in q:
            circ << (H, [i])
            circ << (X, [i])
        if n > 1:
            mcg_z = MultiControlledGateBuilder(n - 1, Z)
            circ << (mcg_z.to_gate(), q)
        for i in q:
            circ << (X, [i])
            circ << (H, [i])

    def __build_oracle(self, circ, dataset, threshold, oracle_q, q, ):
        fun = np.array([(elem - threshold) for elem in dataset])
        if self.__find == 'max':
            fun = np.argwhere(fun >= 0).reshape(-1)
        elif self.__find == 'min':
            fun = np.argwhere(fun <= 0).reshape(-1)
        n = len(q)
        for p in fun:
            num = list(map(int, bin(p)[2:][::-1]))
            idx = [i for i, x in enumerate(num) if x == 1]
            for i in idx:
                circ << (X, q[i])
            mcg = MultiControlledGateBuilder(n, X)
            circ << (mcg.to_gate(), q + oracle_q)
            for i in idx:
                circ << (X, q[i])

    @staticmethod
    def _is_power2(num):
        return num != 0 and ((num & (num - 1)) == 0)
