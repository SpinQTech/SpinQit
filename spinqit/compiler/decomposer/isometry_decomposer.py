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

from typing import List
from spinqit.model import I, Gate, GateBuilder, InverseBuilder
from spinqit.model import DecomposerError
from .diagonal import generate_diagonal_gates
from .multi_controlled_gate import generate_mcg_diagonal
from .uniformly_controlled_gate import generate_ucg_diagonal
import numpy as np
import itertools

phase_epsilon = 1e-10
tolerance = 1e-8

def check_parameter(isometry: np.ndarray):
    n = np.log2(isometry.shape[0])
    m = np.log2(isometry.shape[1])
    if not n.is_integer() or n < 0:
        raise DecomposerError('The number of rows of an isometry must be a non-negative power of 2.')
    if not m.is_integer() or m < 0:
        raise DecomposerError('The number of columns of an isometry must be a non-negative power of 2.')
    if m > n:
        raise DecomposerError('An isometry must have more rows than columns.')
    iden = np.eye(isometry.shape[1])
    mat = np.conj(isometry.T).dot(isometry)
    if not np.allclose(mat, iden):
        raise DecomposerError('The input matrix has non orthonormal columns.')

def _list_to_int(bl):
    result = 0
    size = len(bl)
    for i in range(size):
        v = bl[size-1-i]
        if v == 1:
            result += 2**i
    return result

def _a_k_s(k, s):
    return k // (2 ** s)

def _b_k_s(k, s):
    return k - (_a_k_s(k, s) * (2 ** s))

def _k_s(k, s):
    if k == 0:
        return 0
    else:
        return _get_binary_of_k(k, s+1)[0]

def _get_binary_of_k(k, qnum):
    binary_string = np.binary_repr(k).zfill(qnum)
    binary = []
    for c in binary_string:
        binary.append(int(c))
    return binary[-qnum:]

def _reverse_state_preparation(state: List, basis_state: int) -> np.ndarray:
    ''' Lemma 2 in Ref.[1] to generate the first sub_gate
    '''
    state = np.array(state)
    r = np.linalg.norm(state)
    if r < phase_epsilon:
        return np.eye(2, 2)
    if basis_state == 0:
        m = np.array([[np.conj(state[0]), np.conj(state[1])], [-state[1], state[0]]]) / r
    else:
        m = np.array([[-state[1], state[0]], [np.conj(state[0]), np.conj(state[1])]]) / r
    return m

def update_diagonal_matrix(global_diag, qubit_indexes, local_diag, num_qubits):
    if not global_diag:
        return
    basis_states = list(itertools.product([0, 1], repeat=num_qubits))
    for state in basis_states[: len(global_diag)]:
        state_on_action_qubits = [state[i] for i in qubit_indexes]
        diag_index = _list_to_int(state_on_action_qubits)
        i = _list_to_int(state)
        global_diag[i] *= local_diag[diag_index]

def _get_ucg_gates_for_disentangling(v: np.ndarray, k: int, s: int, n: int):
    if _b_k_s(k, s + 1) == 0:
        i_start = _a_k_s(k, s + 1)
    else:
        i_start = _a_k_s(k, s + 1) + 1
    id_list = [np.eye(2, 2) for _ in range(i_start)]
    base_state = _k_s(k, s)
    gates = [
        _reverse_state_preparation(
            [v[2 * i * 2 ** s + _b_k_s(k, s), 0],
             v[(2 * i + 1) * 2 ** s + _b_k_s(k, s), 0]],
            base_state,
        )
        for i in range(i_start, 2 ** (n - s - 1))
    ]
    return id_list + gates

def check_ucg_is_identity(gates: np.ndarray) -> bool:
    if np.abs(gates[0][0, 0]) < phase_epsilon:
        return False
    for gate in gates:
        if not np.allclose(gate / gates[0][0, 0], np.eye(2, 2)):
            return False
    return True

def _get_basis_states(free_states: List, ctrl_indexes: List, target_index: int):
    l1 = []
    l2 = []
    j = 0
    qnum = len(free_states) + len(ctrl_indexes) + 1
    for i in range(qnum):
        if i in ctrl_indexes:
            l1.append(1)
            l2.append(1)
        elif i == target_index:
            l1.append(0)
            l2.append(1)
        else:
            l1.append(free_states[j])
            l2.append(free_states[j])
            j += 1
    re1 = _list_to_int(l1)
    re2 = _list_to_int(l2)
    return re1, re2

def update_remaining_with_mcg(remaining: np.ndarray, gate: np.ndarray, ctrl_indexes: List, target_index: int):
    num_qubits = int(np.log2(remaining.shape[0]))
    num_cols = remaining.shape[1]
    ctrl_indexes.sort()
    free_qubits = num_qubits - len(ctrl_indexes) - 1
    basis_states_free = list(itertools.product([0, 1], repeat=free_qubits))
    for state_free in basis_states_free:
        (e1, e2) = _get_basis_states(state_free, ctrl_indexes, target_index)
        for i in range(num_cols):
            remaining[np.array([e1, e2]), np.array([i, i])] = np.ndarray.flatten(
                gate.dot(np.array([[remaining[e1, i]], [remaining[e2, i]]]))
            ).tolist()

def update_remaining_with_diag(remaining: np.ndarray, diag: np.ndarray, qubit_indexes: List):
    num_qubits = int(np.log2(remaining.shape[0]))
    num_cols = remaining.shape[1]
    basis_states = list(itertools.product([0, 1], repeat=num_qubits))
    for state in basis_states:
        state_on_action_qubits = [state[i] for i in qubit_indexes]
        diag_index = _list_to_int(state_on_action_qubits)
        i = _list_to_int(state)
        for j in range(num_cols):
            remaining[i, j] = diag[diag_index] * remaining[i, j]

def update_remaining_with_ucg(remaining: np.ndarray, ctrl_num: int, gates: List):
    qubit_num = int(np.log2(remaining.shape[0]))
    column_num = remaining.shape[1]
    spacing = 2 ** (qubit_num - ctrl_num - 1)
    for j in range(2 ** (qubit_num - 1)):
        i = (j // spacing) * spacing + j
        gate_index = i // (2 ** (qubit_num - ctrl_num))
        for col in range(column_num):
            remaining[np.array([i, i + spacing]), np.array([col, col])] = np.ndarray.flatten(
                gates[gate_index].dot(np.array([[remaining[i, col]], [remaining[i + spacing, col]]]))
            ).tolist()
    

def _merge_ucg_and_diag(gates: List, diag: np.ndarray):
    for (i, gate) in enumerate(gates):
        gates[i] = np.array([[diag[2 * i], 0.0], [0.0, diag[2 * i + 1]]]).dot(gate)
    return gates

def decompose_column(remaining: np.ndarray, col_idx: int, s_idx: int, total_qnum: int, builder: GateBuilder, diag: List):
    '''Disentangle qubits one by one in a column
    '''
    # add MCG if necessary
    even_index = 2 * _a_k_s(col_idx, s_idx + 1) * (2 ** s_idx) + _b_k_s(col_idx, s_idx + 1)
    odd_index = (2 * _a_k_s(col_idx, s_idx + 1) + 1) * (2 ** s_idx) + _b_k_s(col_idx, s_idx + 1)
    target_index = total_qnum - s_idx - 1
    
    if _k_s(col_idx, s_idx) == 0 and _b_k_s(col_idx, s_idx+1) != 0 and np.abs(remaining[odd_index, 0]) > phase_epsilon:
        gate_mat = _reverse_state_preparation([remaining[even_index, 0], remaining[odd_index, 0]], 0)
        control_indexes = [ i for i, x in enumerate(_get_binary_of_k(col_idx, total_qnum)) if x == 1 and i != target_index ]
        
        mcg, mcg_diag = generate_mcg_diagonal(gate_mat, len(control_indexes))
        ctrl_pos = [total_qnum - i - 1 for i in control_indexes[::-1]]
        target_pos = s_idx

        builder.append(mcg, [target_pos] + ctrl_pos)

        update_remaining_with_mcg(remaining, gate_mat, control_indexes, target_index)

        mcg_diag_inverse = np.conj(mcg_diag).tolist()

        update_remaining_with_diag(remaining, mcg_diag_inverse, control_indexes+[target_index])
        
        update_diagonal_matrix(diag, control_indexes+[target_index], mcg_diag_inverse, total_qnum)

    # add the UCG to disentangle the qubit, decompose it here
    sub_gates = _get_ucg_gates_for_disentangling(remaining, col_idx, s_idx, total_qnum)
    if not check_ucg_is_identity(sub_gates):
        control_indexes = list(range(target_index))
        ctrl_pos = [total_qnum - i - 1 for i in control_indexes[::-1]]
        target_pos = s_idx
        ucg, ucg_diag = generate_ucg_diagonal(sub_gates, True)
        builder.append(ucg, [target_pos] + ctrl_pos)

        ucg_diag_inverse = np.conj(ucg_diag).tolist()
        _merge_ucg_and_diag(sub_gates, ucg_diag_inverse)
        update_remaining_with_ucg(remaining, len(control_indexes), sub_gates)
        update_diagonal_matrix(diag, control_indexes+[target_index], ucg_diag_inverse, total_qnum)

def check_diag_is_identity(diag: List) -> bool:
    if np.abs(diag[0]) < phase_epsilon:
        return False
    for d in diag:
        if not np.abs(d / diag[0] - 1.0) < phase_epsilon:
            return False
    return True

def build_gate_for_isometry(isometry: np.ndarray) -> Gate:
    '''Reference: 1. https://arxiv.org/abs/1501.06911
    '''
    if len(isometry.shape) == 1:
        isometry = isometry.reshape(isometry.shape[0], 1)
    check_parameter(isometry)

    remaining_columns = isometry.astype(complex)
    qubit_num = int(np.log2(isometry.shape[0]))
    dec_builder = GateBuilder(qubit_num)
    
    diag_mat = []
    for column_idx in range(isometry.shape[1]):
        # decompose_column
        for i in range(qubit_num):
            decompose_column(remaining_columns, column_idx, i, qubit_num, dec_builder, diag_mat)

        diag_mat.append(remaining_columns[column_idx, 0])
        remaining_columns = remaining_columns[:, 1:]
    
    if dec_builder.size() == 0:
        dec_builder.append(I, [0])

    inv_builder = InverseBuilder(dec_builder.to_gate())
    isometry_builder = GateBuilder(qubit_num)

    if len(diag_mat) > 1 and not check_diag_is_identity(diag_mat):
        diag_gate = generate_diagonal_gates(diag_mat)
        isometry_builder.append(diag_gate, list(range(qubit_num)))
    
    isometry_builder.append(inv_builder.to_gate(), list(range(qubit_num-1, -1, -1)))
    return isometry_builder.to_gate()
