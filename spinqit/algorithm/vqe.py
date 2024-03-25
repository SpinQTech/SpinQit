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

from spinqit.model import Circuit, Parameter, Rx, Rz, CX
from spinqit.interface.qlayer import QLayer
from .optimizer import Optimizer
from .loss import expval


class VQE(object):
    def __init__(self,
                 hamiltonian: Union[List, scipy.sparse.csr_matrix],
                 optimizer: Optimizer,
                 ansatz: Circuit = None,
                 params: Union[tuple, np.ndarray] = None,
                 depth: int = 1):
        if isinstance(hamiltonian, list):
            self.__qubit_num = len(hamiltonian[0][0])
        elif isinstance(hamiltonian, scipy.sparse.csr_matrix):
            self.__qubit_num = int(np.log2(hamiltonian.get_shape()[0]))
        else:
            raise ValueError(
                f'The `hamiltonian` should be `list` or `sparse.csr_matrix`, but got {type(hamiltonian)} '
            )
        
        self.optimizer = optimizer
        self.fn = None
        self.hamiltonian = hamiltonian
        if params is not None:
            if isinstance(params, tuple):
                params = np.random.uniform(0, 2 * np.pi, params)
            self.params = Parameter(params, trainable=True)
        else:
            self.__depth = depth
            self.params = Parameter(np.random.uniform(0, 2 * np.pi, (depth, self.__qubit_num, 3)),
                                    trainable=True)
        if ansatz is not None:
            self.circuit = ansatz
        else:
            self.circuit = self.build_ansatz()

    def build_ansatz(self) -> Circuit:
        circ = Circuit()
        qreg = circ.allocateQubits(self.__qubit_num)
        params = circ.add_params(shape=self.params.shape)
        for d in range(self.__depth):
            for q in range(self.__qubit_num):
                circ << (Rx, qreg[q], params[d][q][0])
                circ << (Rz, qreg[q], params[d][q][1])
                circ << (Rx, qreg[q], params[d][q][2])
            if self.__qubit_num > 1:
                for q in range(self.__qubit_num - 1):
                    circ.append(CX, [qreg[q], qreg[q + 1]])
                circ.append(CX, [qreg[self.__qubit_num - 1], qreg[0]])
        return circ

    def run(self, mode='spinq', grad_method='adjoint_differentiation', **kwargs):
        self.fn = self.set_qlayer(self.hamiltonian, mode, grad_method, **kwargs)
        loss_list = self.optimizer.optimize(self.fn, self.params)
        return loss_list

    @property
    def optimized_result(self):
        if self.fn is None:
            raise ValueError(
                f'Use {self.__class__.__name__}.run() to optimize the parameterized quantum circuit first.')
        return self.fn.get_measurement_result((self.params,))

    @property
    def optimized_params(self):
        return self.params

    def set_qlayer(self, hamiltonian, mode, grad_method, **kwargs):
        return QLayer(self.circuit,
                      backend_mode=mode,
                      grad_method=grad_method,
                      measure=expval(hamiltonian),
                      **kwargs)
