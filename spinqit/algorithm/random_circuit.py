# Copyright 2021-2022 SpinQ Technology Co., Ltd.
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
from spinqit import Circuit
from spinqit.model import H, X, Y, Z, Rx, Ry, Rz, T, Td, S, Sd, P, CX, CY, CZ, SWAP, CCX, U, circuit
import numpy as np

single_qubit_gates = [H, X, Y, Z, Rx, Ry, Rz, T, Td, S, Sd, P, U]
two_qubit_gates = [CX, CY, CZ, SWAP]
three_qubit_gates = [CCX]
one_param_gates = {Rx, Ry, Rz, P}
three_param_gates = {U}

def generate_random_circuit(qubit_num: int, depth: int, seed: int = None) -> Circuit:
    if seed is None:
        seed = np.random.randint(0, np.iinfo(np.int32).max)
    rng = np.random.default_rng(seed)

    circuit = Circuit()
    q = circuit.allocateQubits(qubit_num)

    for _ in range(depth):
        remaining_qubits = list(range(qubit_num))
        while remaining_qubits:
            max_qubit_num = min(len(remaining_qubits), 3)
            operand_num = rng.choice(range(max_qubit_num)) + 1
            rng.shuffle(remaining_qubits)
            operands = remaining_qubits[:operand_num]
            remaining_qubits = remaining_qubits[operand_num:]
            if operand_num == 1:
                gate = rng.choice(single_qubit_gates)
            elif operand_num == 2:
                gate = rng.choice(two_qubit_gates)
            elif operand_num == 3:
                gate = rng.choice(three_qubit_gates)
            qubits = [q[i] for i in operands]

            if gate in one_param_gates:
                param_num = 1
            elif gate in three_param_gates:
                param_num = 3
            else:
                param_num = 0
            
            if param_num == 0:
                circuit << (gate, qubits)
            else:
                params = [rng.uniform(0, 2*np.pi) for x in range(param_num)]
                circuit << (gate, qubits, params)
    return circuit

            

            
