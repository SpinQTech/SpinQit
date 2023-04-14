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
from autograd import grad as _grad

from spinqit.algorithm.optimizer import Optimizer
from spinqit.model import Circuit, Instruction
from spinqit.compiler.ir import IntermediateRepresentation as IR
from spinqit.primitive import PauliBuilder, calculate_pauli_expectation


def fubini_tensor(expval_fn, params):
    """
    For now, the function only supports the 'diag' approximation.
    """

    def convert_ob(qubit, pstr):
        h_part = PauliBuilder(pstr).to_gate()
        temp_circ << (h_part, qubit)
        expval_fn.update_backend_config(qubits=qubit)
        result = expval_fn.execute(temp_circ)
        value = calculate_pauli_expectation('Z', result.probabilities)
        temp_circ.instructions.pop()
        return (1 - value * value) / 4

    qubit_num = expval_fn.qubits_num
    ir = expval_fn.check_circuit_get_compiler(expval_fn.circuit).compile(expval_fn.circuit,  expval_fn.optimization_level)

    # Create a temporary circuit to construct the metric tensor
    temp_circ = Circuit()
    temp_circ.allocateQubits(qubit_num)
    Fubini_study_tensor = np.zeros(shape=params.shape)

    generator = {'Rx': 'X', 'Ry': 'Y', 'Rz': 'Z'}
    for v in ir.dag.vs:
        # Fubini tensor index
        if v['type'] == 0:
            label = v['name']
            # if label == 'cnot':
            #     label = 'cx'

            # The observables corresponding to the generators of the gates in the layer:
            if v['trainable']:
                coeff = _grad(v['trainable'])(params)
                val = convert_ob(v['qubits'], generator[label])
                Fubini_study_tensor += coeff * coeff * val

            temp_circ.append_instruction(Instruction(IR.get_basis_gate(label), v['qubits'], [], v['params']))

    Fubini_study_tensor[Fubini_study_tensor == 0] = np.inf
    inv_tensor = 1 / Fubini_study_tensor
    return inv_tensor


class QuantumNaturalGradient(Optimizer):
    def __init__(self,
                 maxiter: int = 1000,
                 tolerance: float = 1e-6,
                 learning_rate: float = 0.01,
                 verbose=True, ):

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

        loss, first_grads = expval_fn.backward()
        Fubini_study_tensor_inv = fubini_tensor(expval_fn, params, )
        derivative = Fubini_study_tensor_inv * first_grads
        params -= self.__learning_rate * derivative
        expval_fn.update(params)
        return loss
