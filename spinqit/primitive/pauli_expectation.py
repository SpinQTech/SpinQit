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
from typing import Dict, List, Union

import itertools
from functools import reduce
import numpy as np
from scipy import sparse
from spinqit import I, X, Y, Z


def calculate_pauli_expectation(pauli_string: str, probabilities: Dict) -> float:
    """
    The qubits string that return is LSB. The qubit index increased from left to right.
    For example:
                '0          0           1'
             qubit[0]    qubit[1]     qubit[2]
    """
    imat = np.array([1, 1])
    zmat = np.array([1, -1])
    mat = []

    for i, ch in enumerate(pauli_string):
        if ch.upper() in ['X', 'Y', 'Z']:
            mat.append(zmat)
        elif ch.upper() == 'I':
            mat.append(imat)
        else:
            raise ValueError('The input string is not a Pauli string')

    f = reduce(np.kron, mat)
    expect_value = 0.0
    for key, value in probabilities.items():
        idx = int(key, 2)
        expect_value += f[idx] * value
    return expect_value



def generate_hamiltonian_matrix(pauli_string_list: List) -> sparse.csr_matrix:
    imat = sparse.identity(2, format='csr')
    xmat = sparse.csr_matrix(X.matrix())
    ymat = sparse.csr_matrix(Y.matrix())
    zmat = sparse.csr_matrix(Z.matrix())

    qubit_num = len(pauli_string_list[0][0])
    ham_mat = sparse.csr_matrix((2 ** qubit_num, 2 ** qubit_num), dtype=np.complex64)

    for pauli_string, coeffi in pauli_string_list:
        umat = 1
        for ch in pauli_string:
            if ch.capitalize() == 'Z':
                umat = sparse.kron(umat, zmat, format='csr')
            elif ch.capitalize() == 'I':
                umat = sparse.kron(umat, imat, format='csr')
            elif ch.capitalize() == 'Y':
                umat = sparse.kron(umat, ymat, format='csr')
            elif ch.capitalize() == 'X':
                umat = sparse.kron(umat, xmat, format='csr')
        ham_mat += coeffi * umat
    return ham_mat

def _pauli_decompose_sparse(hamiltonian):
    h = sparse.csr_matrix(hamiltonian, dtype=np.complex128, copy=True)
    size, cols = h.shape
    if size < 2 or size != cols or (size & (size - 1)):
        raise ValueError("The size of Hamiltonian is not correct.")

    h.sum_duplicates()
    h.eliminate_zeros()

    diff = (h - h.getH()).tocoo()
    if diff.nnz:
        values = np.asarray(h[diff.row, diff.col]).ravel()
        adjoint = np.asarray(h[diff.col, diff.row]).ravel().conj()
        if not np.allclose(values, adjoint):
            raise ValueError("The input Hamiltonian is not Hermitian")

    if h.nnz == 0:
        return []

    coo = h.tocoo()
    flips = coo.row ^ coo.col
    order = np.argsort(flips)
    split_at = np.flatnonzero(np.diff(flips[order])) + 1
    n_qubits = size.bit_length() - 1
    buffer = np.zeros(size, dtype=np.complex128)
    terms = []

    for group in np.split(order, split_at):
        x = int(flips[group[0]])
        buffer.fill(0)
        buffer[coo.row[group]] = coo.data[group]

        width = 1
        while width < size:
            blocks = buffer.reshape(-1, 2 * width)
            left = blocks[:, :width].copy()
            right = blocks[:, width:]
            blocks[:, :width] = left + right
            blocks[:, width:] = left - right
            width *= 2
        buffer /= size

        for z in np.flatnonzero(np.abs(buffer) > 1e-8):
            z = int(z)
            phase = 1j ** bin(x & z).count("1")  
            coeff = np.real_if_close(phase * buffer[z]).item()
            if abs(coeff) > 1e-8:
                label = "".join(
                    "IZXY"[2 * ((x >> bit) & 1) + ((z >> bit) & 1)]
                    for bit in range(n_qubits - 1, -1, -1)
                )
                terms.append((label, coeff))

    terms.sort()
    return terms

def pauli_decompose(hamiltonian: Union[np.ndarray, sparse.csr_matrix]) -> List:
    if sparse.issparse(hamiltonian):
        return _pauli_decompose_sparse(hamiltonian)

    n = int(np.log2(len(hamiltonian)))
    N =  2**n

    if hamiltonian.shape != (N, N):
        raise ValueError('The size of Hamiltonian is not correct.')

    if not np.allclose(hamiltonian, hamiltonian.conj().T):
        raise ValueError('The input Hamiltonian is not Hermitian')

    matrices = [I.matrix(), X.matrix(), Y.matrix(), Z.matrix()]
    labels = [I.label, X.label, Y.label, Z.label]

    indices = [0, 1, 2, 3]
    decomposition = []
    for item in itertools.product(indices, repeat=n):
        gate_mat_list = [matrices[i] for i in item]
        coeff = np.trace(reduce(np.kron, gate_mat_list) @ hamiltonian) / N
        coeff = np.real_if_close(coeff).item()

        if not np.allclose(coeff, 0):
            gate_list = reduce(lambda x,y: x+y, [labels[i] for i in item])
            decomposition.append((gate_list, coeff))

    return decomposition