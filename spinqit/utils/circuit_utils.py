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

from functools import reduce
from typing import List, Iterable, Optional

import numpy as np
from numpy.random import default_rng


DEFAULT_RNG = default_rng()

def print_circuit(circuit):
    from spinqit.compiler.ir import IntermediateRepresentation as IR
    final_list = []
    for i in circuit.instructions:
        if i.gate not in IR.basis_set:
            ilist = print_gate_factors(i.gate, i.qubits, i.params)
            final_list.extend(ilist)
        else:
            final_list.append(i)
    return final_list


def circuit_matrix(circuit):
    return gate_matrix(print_circuit(circuit), circuit.qubits_num, circuit.qubits)


def print_gate_factors(gate, qubit, params=None) -> List:
    r"""
    The gate constructed by other basis gate which is included in the gate factors.
    Decompose the gate into basis gate

    Args:
        gate: class `Gate`
        qubit: List, The qubit list which contains qubits that gate applied on
        params: Optional[float,callable], default to None, params are only callable function or (int, float, numpy dtype)

    Return:
        List of Instruction
    """
    from spinqit.compiler.translator.gate_converter import decompose_multi_qubit_gate, decompose_single_qubit_gate
    from spinqit import Instruction
    from spinqit.compiler.ir import IntermediateRepresentation as IR
    if gate in IR.basis_set:
        res = [Instruction(gate, qubit, [], params)]
    else:
        if gate.qubit_num == 1:
            res = decompose_single_qubit_gate(gate,
                                              qubit,
                                              None if not params else params, )
        else:
            res = decompose_multi_qubit_gate(gate,
                                             qubit,
                                             None if not params else params, )
    return res


def gate_matrix(gate, qubit_num: int, qubit=None) -> np.ndarray:
    r"""
    Calculate the gate matrix, while gate_list can be obtained by func `print_gate_factors`,
    which decompose the gate and return the gate_list (Instruction list)

    Args:
        gate (List[Instruction]): List of Instruction
        qubit_num (int): number of qubit
        qubit (list) : List of qubit index

    Return:
        matrix: np.ndarray
    """
    if isinstance(gate, list):
        gate_list = []
        for g in gate:
            gate_list += print_gate_factors(g.gate, g.qubits, g.params)
    else:
        if qubit is None:
            qubit = list(range(qubit_num))
        gate_list = print_gate_factors(gate, qubit, qubit_num)

    matrix = np.identity(2 ** qubit_num)
    for inst in gate_list:
        gate, qubit, param = inst.gate, inst.qubits, inst.params
        matrix = _gate_matrix(matrix, qubit_num, qubit, gate.get_matrix(param))
    return matrix


def generate_swap_list(num_qubits, qubit_idx):
    origin_seq = list(range(num_qubits))
    seq_for_acted = qubit_idx + [x for x in origin_seq if x not in qubit_idx]
    swapped = [False] * num_qubits
    swap_ops = []
    for idx in range(num_qubits):
        if not swapped[idx]:
            next_idx = idx
            swapped[next_idx] = True
            while not swapped[seq_for_acted[next_idx]]:
                swapped[seq_for_acted[next_idx]] = True
                if next_idx < seq_for_acted[next_idx]:
                    swap_ops.append((next_idx, seq_for_acted[next_idx]))
                else:
                    swap_ops.append((seq_for_acted[next_idx], next_idx))
                next_idx = seq_for_acted[next_idx]
    return swap_ops


def reshape_state(state, swap_ops, num_qubits, higher_dims, perm):
    dim = 2
    for swap_op in swap_ops:
        shape = higher_dims.copy()
        last_idx = -1
        for idx in swap_op:
            shape.append(dim ** (idx - last_idx - 1))
            shape.append(dim)
            last_idx = idx
        shape.append(dim ** (dim * num_qubits - last_idx - 1))
        state = np.transpose(np.reshape(state, shape), perm)
    return state


def _gate_matrix(state, num_qubits, qubit_idx, gate):
    higher_dims = list(state.shape[:-2])
    num_higher_dims = len(higher_dims)
    if not isinstance(qubit_idx, Iterable):
        qubit_idx = [qubit_idx]

    num_acted_qubits = len(qubit_idx)
    perm = list(range(num_higher_dims)) + [item + num_higher_dims for item in [0, 3, 2, 1, 4]]

    swap_ops = generate_swap_list(num_qubits, qubit_idx)
    state = np.reshape(
        reshape_state(state, swap_ops, num_qubits, higher_dims, perm),
        higher_dims + [2 ** num_acted_qubits, 2 ** (2 * num_qubits - num_acted_qubits)]
    )
    state = np.matmul(gate, state)
    swap_ops.reverse()
    state = np.reshape(
        reshape_state(state, swap_ops, num_qubits, higher_dims, perm),
        higher_dims + [2 ** num_qubits, 2 ** num_qubits]
    )
    return state


def nkron(gate_list):
    return reduce(np.kron, gate_list)


def random_unitary(dims, seed=None):
    """Return a random unitary matrix. The operator is sampled from the unitary Haar measure.

    Args:
        dims (int or tuple): the input dimensions of the Operator.
        seed (int or np.random.Generator): Optional. Set a fixed seed or
                                           generator for RNG.

    Returns:
        np.ndarray: Matrix
    """
    if seed is None:
        random_state = DEFAULT_RNG
    elif isinstance(seed, np.random.Generator):
        random_state = seed
    else:
        random_state = default_rng(seed)

    dim = np.product(dims)
    from scipy import stats

    mat = stats.unitary_group.rvs(dim, random_state=random_state)
    return mat


def haar_density_operator(num_qubits: int, rank: Optional[int] = None,
                          is_real: Optional[bool] = False):
    r""" randomly generate a density matrix following Haar random
        Args:
            num_qubits: number of qubits
            rank: rank of density matrix, default to be False refering to full ranks
            is_real: whether the density matrix is real, default to be False
        Returns:
            a :math:`2^n \times 2^n` density matrix
    """
    dim = 2 ** num_qubits
    rank = rank if rank is not None else dim
    assert 0 < rank <= dim, 'rank is an invalid number'
    if is_real:
        ginibre_matrix = np.random.randn(dim, rank)
        rho = ginibre_matrix @ ginibre_matrix.T
    else:
        ginibre_matrix = np.random.randn(dim, rank) + 1j * np.random.randn(dim, rank)
        rho = ginibre_matrix @ ginibre_matrix.conj().T
    rho = rho / np.trace(rho)
    return rho / np.trace(rho)
