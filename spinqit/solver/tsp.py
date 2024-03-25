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
from typing import List, Union
import numpy as np
from collections import Counter
from spinqit.algorithm import VQE, TorchOptimizer
from spinqit.primitive import generate_hamiltonian_matrix
from spinqit import Circuit, PlaceHolder, Parameter, get_compiler, check_backend_and_config
from spinqit import X, Ry, CX, CZ, CSWAP

class TSPSolver:
    def __init__(self, vertex_num: int, weighted_adjacency: Union[List, np.ndarray], penalty: float):
        self.vertex_num = vertex_num
        self.weighted_adjacency = weighted_adjacency
        self.penalty = penalty

    def tsp_graph_to_hamiltonian(self) -> List:
        hamiltonian_list = []
        qubit_num = (self.vertex_num - 1) ** 2
        
        #objective
        for i in range(self.vertex_num - 1):
            for j in range(self.vertex_num - 1):
                if i != j:
                    # weight
                    l_ij = self.weighted_adjacency[i][j]
                    
                    for t in range(self.vertex_num - 2):
                        pauli_list_1 = ['I'] * qubit_num
                        pauli_list_2 = ['I'] * qubit_num
                        pauli_list_3 = ['I'] * qubit_num
                        pauli_list_4 = ['I'] * qubit_num

                        pauli_list_2[i * (self.vertex_num - 1) + t] = 'Z'
                        pauli_list_3[j * (self.vertex_num - 1) + t + 1] = 'Z'
                        pauli_list_4[i * (self.vertex_num - 1) + t] = 'Z'
                        pauli_list_4[j * (self.vertex_num - 1) + t + 1] = 'Z'

                        hamiltonian_list.append((''.join(pauli_list_1), l_ij / 4))
                        hamiltonian_list.append((''.join(pauli_list_2), -l_ij / 4))
                        hamiltonian_list.append((''.join(pauli_list_3), -l_ij / 4))
                        hamiltonian_list.append((''.join(pauli_list_4), l_ij / 4))

            pauli_list_11 = ['I'] * qubit_num
            pauli_list_22 = ['I'] * qubit_num
            pauli_list_33 = ['I'] * qubit_num
            pauli_list_44 = ['I'] * qubit_num

            pauli_list_22[i * (self.vertex_num - 1) + (self.vertex_num - 2)] = 'Z'
            pauli_list_44[i * (self.vertex_num - 1)] = 'Z'

            hamiltonian_list.append((''.join(pauli_list_11), self.weighted_adjacency[self.vertex_num - 1][i] / 2))
            hamiltonian_list.append((''.join(pauli_list_22), -self.weighted_adjacency[self.vertex_num - 1][i] / 2))
            hamiltonian_list.append((''.join(pauli_list_33), self.weighted_adjacency[i][self.vertex_num - 1] / 2))
            hamiltonian_list.append((''.join(pauli_list_44), -self.weighted_adjacency[i][self.vertex_num - 1] / 2))

        # first constraint
        for t in range(self.vertex_num - 1):
            all_I_str = ['I'] * qubit_num
            hamiltonian_list.append((''.join(all_I_str), self.penalty))
            for i in range(self.vertex_num - 1):
                pauli_list_111 = ['I'] * qubit_num
                pauli_list_222 = ['I'] * qubit_num
                pauli_list_333 = ['I'] * qubit_num
                pauli_list_444 = ['I'] * qubit_num

                pauli_list_222[t * (self.vertex_num - 1) + i] = 'Z'
                pauli_list_444[t * (self.vertex_num - 1) + i] = 'Z'

                hamiltonian_list.append((''.join(pauli_list_111), - self.penalty))
                hamiltonian_list.append((''.join(pauli_list_222), self.penalty))
                hamiltonian_list.append((''.join(pauli_list_333), self.penalty / 2))
                hamiltonian_list.append((''.join(pauli_list_444), -self.penalty / 2))

                for j in range(i):
                    pauli_list_5 = ['I'] * qubit_num
                    pauli_list_6 = ['I'] * qubit_num
                    pauli_list_7 = ['I'] * qubit_num
                    pauli_list_8 = ['I'] * qubit_num

                    pauli_list_6[t * (self.vertex_num - 1) + i] = 'Z'
                    pauli_list_7[t * (self.vertex_num - 1) + j] = 'Z'
                    pauli_list_8[t * (self.vertex_num - 1) + i] = 'Z'
                    pauli_list_8[t * (self.vertex_num - 1) + j] = 'Z'

                    hamiltonian_list.append((''.join(pauli_list_5), self.penalty / 2))
                    hamiltonian_list.append((''.join(pauli_list_6), -self.penalty / 2))
                    hamiltonian_list.append((''.join(pauli_list_7), -self.penalty / 2))
                    hamiltonian_list.append((''.join(pauli_list_8), self.penalty / 2))

        # second constraint
        for i in range(self.vertex_num - 1):
            all_I_str = ['I'] * qubit_num
            hamiltonian_list.append((''.join(all_I_str), self.penalty))
            for t in range(self.vertex_num - 1):
                pauli_list_9 = ['I'] * qubit_num
                pauli_list_10 = ['I'] * qubit_num
                pauli_list_11 = ['I'] * qubit_num
                pauli_list_12 = ['I'] * qubit_num

                pauli_list_10[t * (self.vertex_num - 1) + i] = 'Z'
                pauli_list_12[t * (self.vertex_num - 1) + i] = 'Z'

                hamiltonian_list.append((''.join(pauli_list_9), -self.penalty))
                hamiltonian_list.append((''.join(pauli_list_10), self.penalty))
                hamiltonian_list.append((''.join(pauli_list_11), self.penalty / 2))
                hamiltonian_list.append((''.join(pauli_list_12), -self.penalty / 2))

                for k in range(t):
                    pauli_list_1111 = ['I'] * qubit_num
                    pauli_list_12 = ['I'] * qubit_num
                    pauli_list_13 = ['I'] * qubit_num
                    pauli_list_14 = ['I'] * qubit_num

                    pauli_list_12[t * (self.vertex_num - 1) + i] = 'Z'
                    pauli_list_13[k * (self.vertex_num - 1) + i] = 'Z'
                    pauli_list_14[t * (self.vertex_num - 1) + i] = 'Z'
                    pauli_list_14[k * (self.vertex_num - 1) + i] = 'Z'

                    hamiltonian_list.append((''.join(pauli_list_1111), self.penalty / 2))
                    hamiltonian_list.append((''.join(pauli_list_12), -self.penalty / 2))
                    hamiltonian_list.append((''.join(pauli_list_13), -self.penalty / 2))
                    hamiltonian_list.append((''.join(pauli_list_14), self.penalty / 2))
        count = Counter()
        for pstr, coeff in hamiltonian_list:
            count[pstr] += coeff
        hamiltonian_list = []
        for k, v in count.items():
            hamiltonian_list.append((k, v))

        return hamiltonian_list

    def backtrack(self, circ: Circuit, qubits: List, params: PlaceHolder, k: int, vnum: int):
        if k == 2:
            circ << (X, qubits[0])
            circ << (Ry, qubits[1], params[0])
            circ << (CZ, [qubits[0], qubits[1]])
            circ << (Ry, qubits[1], -1*params[0])
            circ << (CX, [qubits[1], qubits[0]])
            circ << (CX, [qubits[1], qubits[vnum]])
            circ << (CX, [qubits[0], qubits[vnum+1]])
            return
        self.backtrack(circ, qubits, params, k-1, vnum)
        circ << (X, qubits[(k-1)*vnum])
        for i in range(k-1):
            qubit_idx = (k-1)*vnum+i
            param_idx = ((k-1)*(k-2))//2+i
            circ << (Ry, qubits[qubit_idx + 1], params[param_idx])
            circ << (CZ, [qubits[qubit_idx], qubits[qubit_idx + 1]])
            circ << (Ry, qubits[qubit_idx + 1], -1*params[param_idx])
        for i in range(k-1):
            qubit_idx = (k-1)*vnum+i
            circ << (CX, [qubits[qubit_idx + 1], qubits[qubit_idx]])
        for i in range(k-1):
            qubit_idx = (k-1)*vnum+i
            for j in range(k-1, (k-1)*vnum, vnum):
                circ << (CSWAP, [qubits[qubit_idx], qubits[j], qubits[j - (k-1-i)]])

    def tsp_vqe(self, iter_num: int, backend_mode: str, grad_method: str, learning_rate: float):
        qubit_num = (self.vertex_num - 1) ** 2
        ansatz = Circuit()
        qreg = ansatz.allocateQubits(qubit_num)
        params = ansatz.add_params(shape=(qubit_num-self.vertex_num+1)//2)
        self.backtrack(ansatz, qreg, params, self.vertex_num-1, self.vertex_num-1)
        optimizer = TorchOptimizer(maxiter=iter_num, verbose=True, learning_rate=learning_rate)
        ham = self.tsp_graph_to_hamiltonian()
        ham_mat = generate_hamiltonian_matrix(ham)
        np.random.seed(1000)
        init_params = Parameter(np.random.uniform(-8.5*np.pi, -8.5 * np.pi, (qubit_num-self.vertex_num+1)//2), trainable=True)
        vqe = VQE(ham_mat, optimizer, ansatz, params=init_params)
        vqe.run(mode=backend_mode, grad_method=grad_method)
        return vqe.optimized_result

    def complement_measurement_result(self, measurement_result) -> str:
        result_string = max(measurement_result.probabilities, key=measurement_result.probabilities.get)
        complement_string = ''
        for i in range(0, (self.vertex_num - 1) ** 2, self.vertex_num - 1):
            complement_string += result_string[i:i + self.vertex_num - 1] + '0'
        complement_string = complement_string + '0' * (self.vertex_num - 1) + '1'
        return complement_string


    def decode_answer(self, complement_string):
        solution_list = []
        for t in range(self.vertex_num):
            for i in range(self.vertex_num):
                if complement_string[i * self.vertex_num + t] == '1':
                    solution_list.append((t, i))

        distance_value = 0
        for i in range(len(solution_list) - 1):
            distance_value += self.weighted_adjacency[solution_list[i][1]][solution_list[i + 1][1]]
        distance_value += self.weighted_adjacency[solution_list[-1][1]][solution_list[0][1]]
        
        return solution_list, distance_value

    def solve(self, iterations: int, backend_mode: str, grad_method: str, learning_rate: float = 0.1):
        result = self.tsp_vqe(iterations, backend_mode, grad_method, learning_rate)
        complement_string = self.complement_measurement_result(result)
        solution_list, distance_value = self.decode_answer(complement_string)
        return solution_list, distance_value