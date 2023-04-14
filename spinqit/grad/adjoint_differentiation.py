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
from typing import List, Iterable

import numpy as np
from autograd import grad as _grad
from spinqit.compiler.ir import IntermediateRepresentation as IR
from spinqit import X, Y, Z, I, Rx, Ry, Rz, P


def adjoint_differentiation(ir, config, params, hamiltonian, backend, state):
    qubit_num = ir.qnum
    ket = np.array(backend.execute(ir, config, state, params).states)
    bra = ket.conj() @ hamiltonian

    generator = {
        Rx.label: -0.5 * X.get_matrix(),
        Ry.label: -0.5 * Y.get_matrix(),
        Rz.label: -0.5 * Z.get_matrix(),
        P.label: 0.5 * (I.get_matrix() - Z.get_matrix()),
    }

    # The core function
    def _adjoint_func(bra, ket, ir, params, qubit_num):
        grads = np.zeros_like(params, dtype=float)
        for i in range(ir.dag.vcount() - 1, -1, -1):
            v = ir.dag.vs[i]
            if v['type'] == 0:
                label = v['name']
                qubits = v['qubits']
                if label in generator:
                    mat = IR.get_basis_gate(label).get_matrix(v['params'])
                else:
                    mat = IR.get_basis_gate(label).get_matrix()
                ket = _apply_gate(ket, mat.conj().T, qubits, qubit_num)
                if 'trainable' in v.attributes():
                    if not v['trainable']:
                        pass
                    else:
                        coeff = _grad(v['trainable'])(params)
                        gen_mat = generator[label]
                        d_theta = 1j * gen_mat @ mat
                        tmp_ket = _apply_gate(ket, d_theta, qubits, qubit_num)
                        grads += coeff * 2 * np.real(bra @ tmp_ket)

                bra = _apply_gate(bra.conj(), mat.conj().T, qubits, qubit_num).conj()
        return grads

    return bra@ket, _adjoint_func(bra, ket, ir, params, qubit_num)


def _helper(state, swap_ops, higher_dims, num_qubits, perm):
    for swap_op in swap_ops:
        shape = higher_dims.copy()
        last_idx = -1
        for idx in swap_op:
            shape.append(2 ** (idx - last_idx - 1))
            shape.append(2)
            last_idx = idx
        shape.append(2 ** (num_qubits - last_idx - 1))
        state = state.reshape(shape)
        state = np.transpose(state, perm)
    return state


def _apply_gate(state: np.ndarray, gate: np.ndarray,
                qubit_idx: List[int], num_qubits: int) -> np.ndarray:
    higher_dims = list(state.shape[:-1])
    num_higher_dims = len(higher_dims)

    if not isinstance(qubit_idx, Iterable):
        qubit_idx = [qubit_idx]

    num_acted_qubits = len(qubit_idx)
    origin_seq = list(range(0, num_qubits))
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
    perm = list(range(0, num_higher_dims)) + [item + num_higher_dims for item in [0, 3, 2, 1, 4]]
    state = _helper(state, swap_ops, higher_dims, num_qubits, perm)
    state = np.reshape(state,
                       higher_dims.copy() + [2 ** num_acted_qubits, 2 ** (num_qubits - num_acted_qubits)])
    state = np.matmul(gate, state)
    swap_ops.reverse()
    state = _helper(state, swap_ops, higher_dims, num_qubits, perm)
    state = np.reshape(state, higher_dims.copy() + [2 ** num_qubits])
    return state
