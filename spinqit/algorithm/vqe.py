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

from typing import List, Union

import numpy as np
import scipy.sparse

from spinqit.model import Circuit, Rx, Rz, CX
from .expval import ExpvalCost
from ..model.parameter import Parameter


class VQE(object):
    def __init__(self,
                 qubit_num: int,
                 depth: int,
                 hamiltonian: Union[List, scipy.sparse.csr_matrix],
                 ansatz: Circuit = None,
                 optimizer=None, ):
        """
        Args:
            qubit_num (int): The number of qubits
            depth (int): The number of ansatz repeat times
        """
        self.__qubit_num = qubit_num
        self.__depth = depth
        self.optimizer = optimizer
        self.fn = None
        self.hamiltonian = hamiltonian
        if ansatz is not None:
            self.circuit = self.build(ansatz)
        else:
            self.circuit = self.build()

    def build(self, ansatz=None) -> Circuit:
        if ansatz is None:
            params = Parameter(np.random.uniform(0, 2 * np.pi, 3 * self.__qubit_num * self.__depth),
                               trainable=True)
            circ = Circuit(params)
            qreg = circ.allocateQubits(self.__qubit_num)
            for d in range(self.__depth):
                for q in range(self.__qubit_num):
                    circ << (Rx, qreg[q], lambda x, idx=3 * self.__qubit_num * d + 3 * q: x[idx])
                    circ << (Rz, qreg[q], lambda x, idx=3 * self.__qubit_num * d + 3 * q + 1: x[idx])
                    circ << (Rx, qreg[q], lambda x, idx=3 * self.__qubit_num * d + 3 * q + 2: x[idx])
                if self.__qubit_num > 1:
                    for q in range(self.__qubit_num - 1):
                        circ.append(CX, [qreg[q], qreg[q + 1]])
                    circ.append(CX, [qreg[self.__qubit_num - 1], qreg[0]])
        else:
            circ = Circuit()
            for d in range(self.__depth):
                circ += ansatz
        return circ

    def run(self,  mode='spinq', grad_method='adjoint_differentiation'):
        """
            Args:
                mode (str): The backend mode, only supported `spinq` or `torch`.
                grad_method (str):
                        For `spinq` backend, the grad_method have `param_shift` and `adjoint_differentiation`
                        For `torch` backend, the grad_method have `backprop`

            Return:
                The optimize step loss list.
        """
        if self.optimizer is None:
            raise ValueError(
                'The optimizer should be given in VQE.__init__()'
            )

        optimizer = self.optimizer
        self.set_expval_fn(self.hamiltonian, mode, grad_method)
        loss_list = optimizer.optimize(self.fn, )
        return loss_list

    @property
    def optimized_params(self):
        return self.circuit.params

    @property
    def optimized_result(self):
        """
            Run the circuit that after optimization and get the result(contains states and probability)

            Return:
                Result: Include the states, counts, probability
        """
        if self.fn is None:
            raise ValueError(
                f'Use {self.__class__.__name__}.run() to optimize the parameterized quantum circuit first.')
        result = self.fn.execute(self.circuit)
        return result

    def set_expval_fn(self, hamiltonian, mode, grad_method):
        expvalcost = ExpvalCost(self.circuit,
                                hamiltonian,
                                backend_mode=mode,
                                grad_method=grad_method)
        self.fn = expvalcost
