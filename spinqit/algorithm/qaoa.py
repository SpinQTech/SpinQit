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
from spinqit.model.spinqCloud.gate import Gate
from typing import List, Union

import numpy as np
from scipy import sparse

from spinqit import Parameter
from spinqit.model import Circuit, H, Rx, GateBuilder
from spinqit.model.Ising_gate import Z_IsingGateBuilder, X_IsingGateBuilder, Y_IsingGateBuilder
from spinqit.primitive.pauli_expectation import pauli_decompose
from spinqit.compiler import compiler
from spinqit.interface.qlayer import QLayer
from .optimizer import Optimizer
from .loss import expval


class QAOA(object):
    def __init__(
            self,
            problem: Union[List, sparse.csr_matrix],
            optimizer: Optimizer,
            depth: int,
            problem_ansatz=None,
            mixer_ansatz=None         
    ):
        self.qlayer = None
        self.optimizer = optimizer

        if problem_ansatz is None:
            if isinstance(problem, list):
                self.__qubit_num = len(problem[0][0])
                problem_ansatz = self._generate_problem_circuit(problem)
            elif isinstance(problem, sparse.csr_matrix):
                self.__qubit_num = int(np.log2(problem.get_shape()[0]))
                problem_ansatz = self._generate_problem_circuit(pauli_decompose(problem.toarray()))
            else:
                raise ValueError(
                    f'The `problem` should be `list` or `sparse.csr_matrix`, but got {type(problem)} '
                )
        self.hamiltonian = problem
        self.__depth = depth
        self.params = Parameter(np.random.uniform(0, 2 * np.pi, (self.__depth*2,))) 
        
        if mixer_ansatz is None:
            mixer_ansatz = self._generate_mixer_circuit()

        self.circuit = self._build(problem_ansatz, mixer_ansatz)

    def _generate_problem_circuit(self, ham) -> Gate:
        builder = GateBuilder(self.__qubit_num)
        if ham is None or not isinstance(ham, list):
            raise ValueError(
                'The problem hamiltonian should be given in list in __init__().'
            )
        for i in range(len(ham)):
            if 'Z' in ham[i][0]:
                qubits = [idx for idx in range(len(ham[i][0])) if ham[i][0][idx] == 'Z']
                rzz = Z_IsingGateBuilder(len(qubits)).to_gate()
                builder.append(rzz, qubits, lambda x: x)
            elif 'X' in ham[i][0]:
                qubits = [idx for idx in range(len(ham[i][0])) if ham[i][0][idx] == 'X']
                rxx = X_IsingGateBuilder(len(qubits)).to_gate()
                builder.append(rxx, qubits, lambda x: x)
            elif 'Y' in ham[i][0]:
                qubits = [idx for idx in range(len(ham[i][0])) if ham[i][0][idx] == 'Y']
                ryy = Y_IsingGateBuilder(len(qubits)).to_gate()
                builder.append(ryy, qubits, lambda x: x)
        return builder.to_gate()

    def _generate_mixer_circuit(self) -> Gate:
        """
        The pauli rotation gate (RX gate)
        """
        builder = GateBuilder(self.__qubit_num)
        for i in range(self.__qubit_num):
            builder.append(Rx, [i], lambda x: x)
        return builder.to_gate()

    @compiler(option='native')
    def _build(self, problem: GateBuilder, mixer: GateBuilder) -> Circuit:
        circ = Circuit()
        qubits = circ.allocateQubits(self.__qubit_num)
        param = circ.add_params(shape=(self.__depth * 2,)) 

        for i in range(len(qubits)):
            circ << (H, qubits[i])

        for i in range(self.__depth):
            circ << (problem, qubits, param[i * 2])
            circ << (mixer, qubits, param[i * 2 + 1])
        return circ

    def run(self, mode='spinq', grad_method='adjoint_differentiation'):
        """
            Args:
                mode (str): The backend mode supports only `spinq` or `torch`.
                grad_method (str):
                        For `spinq` backend, the grad_method is `param_shift` or `adjoint_differentiation`
                        For `torch` backend, the grad_method is `backprop`

            Return:
                The optimize step loss list.
        """
        interface = 'torch' if mode == 'torch' else 'spinq'
        self.qlayer = self.set_qlayer(self.hamiltonian, mode, grad_method, interface)
        loss_list = self.optimizer.optimize(self.qlayer, self.params)
        return loss_list

    def set_qlayer(self, hamiltonian, mode, grad_method, interface):
        return QLayer(self.circuit,
                      backend_mode=mode,
                      grad_method=grad_method,
                      measure=expval(hamiltonian),
                      interface=interface)

    @property
    def optimized_result(self):
        if self.qlayer is None:
            raise ValueError(
                f'Use {self.__class__.__name__}.run() to optimize the parameterized quantum circuit first.')
        return self.qlayer.get_measurement_result((self.params,))

    @property
    def optimized_params(self):
        return self.params

    # @staticmethod
    # def from_graph(graph, ):
    #     if not isinstance(graph, nx.Graph):
    #         raise ValueError(
    #             f"Input graph must be a nx.Graph or rx.PyGraph, got {type(graph).__name__}"
    #         )
    #
    #     graph_nodes = graph.nodes()
    #     graph_edges = graph.edges
    #
    #     # In RX each node is assigned to an integer index starting from 0;
    #     # thus, we use the following lambda function to get node-values.
    #     get_nvalue = lambda i: i
    #
    #     identity_h = [-0.5 for e in graph_edges], [qml.Identity(get_nvalue(e[0])) @ qml.Identity(get_nvalue(e[1])) for e
    #                                                in graph_edges]
    #
    #     H = edge_driver(graph, ["10", "01"]) + identity_h
    #     # store the valuable information that all observables are in one commuting group
    #     H.grouping_indices = [list(range(len(H.ops)))]
