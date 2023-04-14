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

from scipy import sparse

from .expval import ExpvalCost
from spinqit.model import Circuit, H, Rx
from spinqit.model.Ising_gate import Z_IsingGateBuilder, X_IsingGateBuilder, Y_IsingGateBuilder
from spinqit.primitive.pauli_expectation import pauli_decompose
from spinqit import get_compiler


class QAOA(object):
    def __init__(
            self,
            qubit_num: int,
            depth: int,
            problem: Union[List, sparse.csr_matrix],
            mixer: Circuit = None,
            problem_ansatz=None,
            optimizer=None,
    ):

        self.__qubit_num = qubit_num
        self.__depth = depth
        self.fn = None

        self.optimizer = optimizer

        if problem_ansatz is None:
            if isinstance(problem, list):
                problem_ansatz = self._generate_problem_circuit(problem)
            elif isinstance(problem, sparse.csr_matrix):
                problem_ansatz = self._generate_problem_circuit(pauli_decompose(problem.toarray()))
            else:
                raise ValueError(
                    f'The `problem` should be `list` or `sparse.csr_matrix`, but got {type(problem)} '
                )
        self.hamiltonian = problem

        if mixer is None:
            mixer = self._generate_mixer_circuit()

        self.circuit = self._build(problem_ansatz, mixer)

    def _generate_problem_circuit(self, ham):
        """
        Rzz gate
        """
        circ = Circuit(1)
        circ.allocateQubits(self.__qubit_num)
        if ham is None or not isinstance(ham, list):
            raise ValueError(
                'The problem hamiltonian should be given in list in __init__().'
            )
        for i in range(len(ham)):
            if 'Z' in ham[i][0]:
                qubits = [idx for idx in range(len(ham[i][0])) if ham[i][0][idx] == 'Z']
                rzz = Z_IsingGateBuilder(len(qubits)).to_gate()
                circ << (rzz, qubits, lambda x: x[[0]])
            elif 'X' in ham[i][0]:
                qubits = [idx for idx in range(len(ham[i][0])) if ham[i][0][idx] == 'X']
                rxx = X_IsingGateBuilder(len(qubits)).to_gate()
                circ << (rxx, qubits, lambda x: x[[0]])
            elif 'Y' in ham[i][0]:
                qubits = [idx for idx in range(len(ham[i][0])) if ham[i][0][idx] == 'Y']
                ryy = Y_IsingGateBuilder(len(qubits)).to_gate()
                circ << (ryy, qubits, lambda x: x[[0]])
        return circ

    def _generate_mixer_circuit(self):
        """
        The pauli rotation gate (RX gate)
        """
        circ = Circuit(1)
        circ.allocateQubits(self.__qubit_num)
        for i in range(circ.qubits_num):
            circ << (Rx, [i], lambda x: x[0],)
        return circ

    def _build(self, problem: Circuit, mixer: Circuit) -> Circuit:

        circ = Circuit()
        qubits = circ.allocateQubits(self.__qubit_num)

        for i in range(len(qubits)):
            circ << (H, qubits[i])

        for i in range(self.__depth):
            circ += problem
            circ += mixer
        return circ

    def run(self, mode='spinq', grad_method='adjoint_differentiation', ):
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
                f'The optimizer should be given in __init__()'
            )

        optimizer = self.optimizer
        self.set_expval_fn(self.hamiltonian, mode, grad_method)
        loss_list = optimizer.optimize(self.fn)
        return loss_list

    @property
    def optimized_params(self):
        return self.circuit.params

    @property
    def optimized_result(self):
        if self.fn is None:
            raise ValueError(
                f'Use {self.__class__.__name__}.run() to optimize the parameterized quantum circuit first.'
            )
        result = self.fn.execute(self.circuit)
        return result

    def set_expval_fn(self, hamiltonian, mode, grad_method):
        expvalcost = ExpvalCost(self.circuit,
                                hamiltonian,
                                backend_mode=mode,
                                grad_method=grad_method)
        self.fn = expvalcost

    def get_measurements(self, backend, config):
        compiler = get_compiler('native')
        ir = compiler.compile(self.circuit, 0)
        return backend.execute(ir, config, params=self.circuit.params)