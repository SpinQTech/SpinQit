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

from spinqit.model import GateBuilder, Rz, Ry, Rx, H, X, Ph
from spinqit.compiler.decomposer import decompose_zyz, build_gate_for_isometry
from spinqit.model import Instruction, PlaceHolder
from spinqit.model.Ising_gate import Z_IsingGateBuilder
from .multi_controlled_gate_builder import MultiControlledGateBuilder

_EPS = 1e-10



def amplitude_encoding(vector: np.ndarray, qubits: List) -> List[Instruction]:
    if len(vector.shape) == 1:
        vector = vector.reshape(vector.shape[0], 1)
    
    nb = int(np.log2(len(vector)))
    if nb != len(qubits):
        raise ValueError
    vector = vector / np.linalg.norm(vector)

    inst_list = []
    if len(qubits) == 1:
        mat = 1 / np.linalg.norm(vector) * np.array(
            [[vector[0, 0], -vector[1, 0].conjugate()],
             [vector[1, 0], vector[0, 0].conjugate()]]
        )
        alpha, beta, gamma, phase = decompose_zyz(mat)

        if abs(alpha - 0.0) > _EPS:
            inst_list.append(Instruction(Rz, qubits, [], alpha))
        if abs(beta - 0.0) > _EPS:
            inst_list.append(Instruction(Ry, qubits, [], beta))
        if abs(gamma - 0.0) > _EPS:
            inst_list.append(Instruction(Rz, qubits, [], gamma))
        if abs(phase - 0.0) >= _EPS:
            inst_list.append(Instruction(Ph, qubits, [], phase))
    else:
        gate = build_gate_for_isometry(vector)
        inst_list.append(Instruction(gate, qubits))

    return inst_list


def dfs_amplitude_encoding(vector, qubits):
    length = vector.shape[0]
    qubit_num = int(np.log2(length))
    vector /= np.linalg.norm(vector)
    gate_builder = GateBuilder(qubit_num)

    @np.vectorize
    def int2bin(x, l):
        return bin(x)[2:].zfill(l)

    def dfs(idx, builder):
        if idx == 1:
            return
        idx //= 2
        n_qubit = int(np.log2(idx))
        if qubit_num - n_qubit - 1 > 0:
            flip = int2bin(list(range(2**(qubit_num - n_qubit-1))), qubit_num - n_qubit-1)
        else:
            flip = ['']
        flip_idx = 0
        for i in range(idx, length, 2 * idx):
            theta = np.arcsin(np.linalg.norm(vector[i:i + idx]) / np.linalg.norm(vector[i - idx: i + idx]))
            mcg = MultiControlledGateBuilder(qubit_num - n_qubit - 1, Ry, 2 * theta).to_gate()
            _flip = flip[flip_idx]
            for _idx, j in enumerate(_flip):
                if j == '0':
                    builder.append(X, _idx)
            builder.append(mcg, list(range(qubit_num - n_qubit)), )
            for _idx, j in enumerate(_flip):
                if j == '0':
                    builder.append(X, _idx)
            flip_idx += 1
        dfs(idx, builder)

    dfs(length, gate_builder)
    return [Instruction(gate_builder.to_gate(), qubits)]


def angle_encoding(vector: Union[np.ndarray, PlaceHolder], qubits: List, depth=1, rotate_gate='ry') -> List[Instruction]:
    r"""
    angle encoding with rotation gates
    """
    if len(vector.shape) == 1:
        vector = vector.reshape(vector.shape[0], 1)

    inst_list = []

    if rotate_gate == 'rx':
        gate = Rx
    elif rotate_gate == 'rz':
        gate = Rz
    else:
        gate = Ry

    for _ in range(depth):
        for i in range(len(vector)):
            inst_list.append(Instruction(gate, [qubits[i]], [], vector[i]))

    return inst_list


def iqp_encoding(vector: Union[np.ndarray, PlaceHolder], qubits: List, depth: int=1, ring_pattern: bool=False) -> List[Instruction]:
    r"""
    Args:
        vector (np.ndarray or PlaceHolder): The vector that want to encode
        qubits (list): qubits list
        depth (int) : The
        ring_pattern (bool): False.
                    when pattern is `ring`, apply rzz gates onto the first and last qubits.
    """
    if len(vector.shape) == 1:
        vector = vector.reshape((vector.shape[0], 1))

    inst_list = []

    for _ in range(depth):
        # Hadamard layer
        for i in qubits:
            inst_list.append(Instruction(H, [i], [], []))

        # Rz layer
        for j in range(len(qubits)):
            inst_list.append(Instruction(Rz, [qubits[j]], [], [vector[j]]))

        # Rzz layer
        for k in range(len(qubits) - 1):
            rzz = Z_IsingGateBuilder(2).to_gate()
            inst_list.append(Instruction(rzz, [qubits[k], qubits[k + 1]], [], [vector[k] * vector[k + 1]]))

        if ring_pattern == True:
            rzz = Z_IsingGateBuilder(2).to_gate()
            inst_list.append(Instruction(rzz, [qubits[-1], qubits[0]], [], [vector[-1] * vector[0]]))

    return inst_list


def basis_encoding(vector:np.ndarray, qubits:List) -> List[Instruction]:
    inst_list = []
    if any(x != 0 and x != 1 for x in vector):
        raise ValueError
    for i in range(vector):
        if vector[i] == 1:
            inst_list.append(Instruction(X, qubits[i]))
    return inst_list

