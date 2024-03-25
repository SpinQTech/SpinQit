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
from typing import Union, List
from math import pi
from scipy.linalg import schur
import numpy as np
from spinqit.model import Gate, Instruction, ControlledGate, MatrixGate, MatrixGateBuilder
from spinqit.model import UnsupportedGateError
from spinqit.model import I, H, X, Y, Z, Rx, Ry, Rz, P, T, Td, S, Sd, CX, CY, CZ, CP, SWAP
from spinqit.compiler.decomposer import decompose_zyz, decompose_two_qubit_gate, build_gate_for_isometry

def generate_power_matrix(mat: np.ndarray, exponent: float) -> np.ndarray:
    decomposition, unitary = schur(mat, output='complex')
    diagonal = decomposition.diagonal()
    if not np.allclose(np.diag(diagonal), decomposition):
        raise ValueError('The matrix is not diagonal.')
    decomposition_power = []
    for dd in diagonal:
        decomposition_power.append(pow(dd, exponent))
    # unitary_power = unitary @ np.diag(decomposition_power) @ unitary.conj().T
    return unitary, np.diag(decomposition_power)

def generate_power_gate(gate: Gate, exponent: Union[int, float], qubits: List, params: List = [], control: bool = False, control_bit: int = None) -> List[Instruction]:
    ''' Generate the instructions that represent the power of a given gate. When control is True and control_bit is set, the instructions represent the controlled power gate.
    '''
    inst_list = []
    global_phase = 0.0
    if (exponent >= 0 and (isinstance(exponent, int) or exponent.is_integer())):
        exponent = int(exponent) 
        if gate in (I, H, X, Y, Z):
            if exponent % 2 == 0:
                inst_list.append(Instruction(I, qubits)) 
            else:
                inst_list.append(Instruction(gate, qubits)) 
        elif gate in (CX, CY, CZ, SWAP):
            if exponent % 2 == 0:
                inst_list.append(Instruction(I, qubits[0]))
                inst_list.append(Instruction(I, qubits[1]))
            else:
                inst_list.append(Instruction(gate, qubits))
        elif gate in (Rx, Ry, Rz, P, CP):
            radian = (params[0] * exponent) % (2 * pi)
            inst_list.append(Instruction(gate, qubits, [], radian))
        elif gate == T:
            radian = (pi / 4 * exponent) % (2 * pi)
            inst_list.append(Instruction(P, qubits, [], radian))
        elif gate == Td:
            radian = (-1 * pi / 4 * exponent) % (2 * pi)
            inst_list.append(Instruction(P, qubits, [], radian))
        elif gate == S:
            radian = (pi / 2 * exponent) % (2 * pi)
            inst_list.append(Instruction(P, qubits, [], radian))
        elif gate == Sd:
            radian = (-1 * pi / 2 * exponent) % (2 * pi)
            inst_list.append(Instruction(P, qubits, [], radian))
        elif isinstance(gate, MatrixGate):
            unitary = gate.get_matrix(*params)
            du, diag = generate_power_matrix(unitary, exponent)
            unitary_power = du @ diag @ du.conj().T
            power_gate_builder = MatrixGateBuilder(unitary_power)
            if gate.qubit_num == 1:
                alpha, beta, gamma, phase = decompose_zyz(unitary_power)
                power_gate_builder.append(Rz, [0], alpha)
                power_gate_builder.append(Ry, [0], beta)
                power_gate_builder.append(Rz, [0], gamma)
                global_phase = phase
            else:
                sub_gate = build_gate_for_isometry(unitary_power)
                qlist = list(range(gate.qubit_num))
                power_gate_builder.append(sub_gate, qlist)
            inst_list.append(Instruction(power_gate_builder.to_gate(), qubits))
        elif gate.qubit_num <= 2 and gate.matrix is not None:
            unitary = gate.get_matrix(*params)
            du, diag = generate_power_matrix(unitary, exponent)
            unitary_power = du @ diag @ du.conj().T
            if gate.qubit_num == 1:
                alpha, beta, gamma, phase = decompose_zyz(unitary_power)
                inst_list.append(Instruction(Rz, qubits, [], alpha))
                inst_list.append(Instruction(Ry, qubits, [], beta))
                inst_list.append(Instruction(Rz, qubits, [], gamma))
                global_phase = phase
            else:
                inst_list.extend(decompose_two_qubit_gate(unitary_power, qubits[0], qubits[1]))
        else:
            for i in range(exponent):
                inst_list.append(Instruction(gate, qubits, [], params))
    else: # power is float, decompose
        if gate.matrix is None:
            raise UnsupportedGateError(gate.label + ' is not supported.')
        unitary = gate.get_matrix(*params)
        du, diag = generate_power_matrix(unitary, exponent)
        unitary_power = du @ diag @ du.conj().T
        
        if isinstance(gate, MatrixGate):
            power_gate_builder = MatrixGateBuilder(unitary_power)
            if gate.qubit_num == 1:
                alpha, beta, gamma, phase = decompose_zyz(unitary_power)
                power_gate_builder.append(Rz, [0], alpha)
                power_gate_builder.append(Ry, [0], beta)
                power_gate_builder.append(Rz, [0], gamma)
                global_phase = phase
            else:
                sub_gate = build_gate_for_isometry(unitary_power)
                qlist = list(range(gate.qubit_num))
                power_gate_builder.append(sub_gate, qlist)
            inst_list.append(Instruction(power_gate_builder.to_gate(), qubits))
        elif gate.qubit_num == 1:
            alpha, beta, gamma, phase = decompose_zyz(unitary_power)
            inst_list.append(Instruction(Rz, qubits, [], alpha))
            inst_list.append(Instruction(Ry, qubits, [], beta))
            inst_list.append(Instruction(Rz, qubits, [], gamma))
            global_phase = phase
        elif gate.qubit_num == 2:
            inst_list.extend(decompose_two_qubit_gate(unitary_power, qubits[0], qubits[1]))
        else:
            power_gate = build_gate_for_isometry(unitary_power)
            inst_list.append(Instruction(power_gate, qubits))
    
    if control:
        for inst in inst_list:
            inst.gate = ControlledGate(inst.gate)
            inst.qubits = [control_bit] + inst.qubits
        if abs(global_phase - 0.0) > 1e-6:
            if len(inst_list) == 1 and isinstance(inst_list[0].gate.subgate, MatrixGate):
                inst_list[0].gate.factors.append((P, [0], lambda *args: global_phase))
            else:
                inst_list.append(Instruction(P, [control_bit], [], global_phase))

    return inst_list