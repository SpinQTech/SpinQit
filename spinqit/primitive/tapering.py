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
from typing import List, Tuple
import numpy as np
import functools

code_to_pauli = {'00':'I', '01':'Z', '10':'X', '11':'Y'}

def to_binary_repr(pauli_str: str) -> np.ndarray:
    qnum = len(pauli_str)
    repr = np.zeros(2*qnum, dtype=np.int)
    for idx in range(qnum):
        op = pauli_str[idx]
        if op == 'X':
            repr[idx] = 1
        elif op == 'Y':
            repr[idx] = 1
            repr[idx + qnum] = 1
        elif op == 'Z':
            repr[idx + qnum] = 1
    return repr

def to_pauli_str(binary_repr: np.ndarray) -> str:
    qnum = len(binary_repr) // 2
    word = ''
    for i in range(qnum):
        if binary_repr[i] == 1 and binary_repr[i + qnum] == 0:
            word += 'X'
        elif binary_repr[i] == 1 and binary_repr[i + qnum] == 1:
            word += 'Y'
        elif binary_repr[i] == 0 and binary_repr[i + qnum] == 1:
            word += 'Z'
        else:
            word += 'I'
    return word

def row_reduce_from_binary(mat: np.ndarray) -> np.ndarray:
    rows, cols = mat.shape
    i=j=0
    while i<rows and j<cols:
        if mat[i][j] == 0:
            non_zero_row = i
            for k in range(i+1, rows):
                if mat[k][j] == 1:
                    non_zero_row = k
                    break
            if mat[non_zero_row][j] == 0:
                j += 1
                continue
            mat[[i, non_zero_row]] = mat[[non_zero_row, i]]

        for k in range(0, rows):
            if k != i and mat[k][j] == 1:
                mat[k] ^= mat[i]
        i += 1; j+= 1
    return mat

def binary_null_space(mat: np.ndarray) -> np.ndarray:
    rows, cols = mat.shape
    pivot_cols = mat.argmax(axis=1)
    free_cols = np.setdiff1d(np.arange(cols), pivot_cols)
    null_space = np.zeros((cols, len(free_cols)), dtype=int)
    null_space[free_cols, np.arange(len(free_cols))] = 1

    null_vector_indices = np.ix_(pivot_cols, np.arange(len(free_cols)))
    binary_vector_indices = np.ix_(np.arange(len(pivot_cols)), free_cols)
    null_space[null_vector_indices] = -mat[binary_vector_indices] % 2
    return null_space.T

def combine_terms(ham: List, eps:float = 1.0e-12) -> List:
    changed = False
    term_map = {}
    for pauli_word, coeff in ham:
        if pauli_word not in term_map:
            term_map[pauli_word] = coeff
        else:
            changed = True
            term_map[pauli_word] += coeff
    if not changed:
        return ham
    result = []
    for k, v in term_map.items():
        if np.abs(v) > eps:
            result.append((k, v))
    return result

def cast_to_binary(ham: List) -> np.ndarray:
    qubit_num = len(ham[0][0])
    bin_mat = np.zeros((len(ham), 2*qubit_num), dtype=int)
    for row, term in enumerate(ham):
        ops = term[0]
        for col, op in enumerate(ops):
            if op in ['X', 'Y']:
                bin_mat[row][col+qubit_num] = 1
            elif op in ['Z', 'Y']:
                bin_mat[row][col] = 1
    return bin_mat

def generate_symmetry_generator(ham: List) -> List:
    qubit_num = len(ham[0][0])
    bin_mat = cast_to_binary(ham)
    rref_mat = row_reduce_from_binary(bin_mat)
    rref_mat_no_zero = rref_mat[~np.all(rref_mat == 0, axis=1)]
    nullspace = binary_null_space(rref_mat_no_zero)
    generators = []
    for nullvec in nullspace:
        pauli_str = ''
        for x,z in zip(nullvec[:qubit_num], nullvec[qubit_num:]):
            pauli_str += code_to_pauli[f"{x}{z}"]
        generators.append((pauli_str, 1.0))
    return generators

def generate_X_qubits(generators: List) -> List:
    bin_mat = cast_to_binary(generators)
    xops = []
    for row in range(bin_mat.shape[0]):
        brow = bin_mat[row]
        rest = np.delete(brow, row, axis=0)
        for col in range(bin_mat.shape[1] // 2, -1, -1):
            if brow[col] and rest[col] == 0:
                xops.append(col)
    return xops

def generate_sector(ham: List, generators: List, active_electrons: int) -> List:
    assert active_electrons > 0, "The number of active electrons must be greater than zero."
    orbitals = np.arange(len(ham[0][0]))

    if active_electrons > len(orbitals):
        raise ValueError("The number of orbitals is smaller than the number of active electrons.")

    bin_hf = np.array([1 if elem < active_electrons else 0 for elem in orbitals])
    result = []
    for pauli_str,_ in generators:
        coding = np.array([1 if s != 'I' else 0 for s in pauli_str])
        eigen = -1 if np.logical_xor.reduce(np.logical_and(coding, bin_hf)) else 1
        result.append(eigen)
    return result

def multiply_pauli_str(word1: str, word2: str) -> Tuple:
    vec1 = to_binary_repr(word1)
    vec2 = to_binary_repr(word2)
    vec_product = vec1 ^ vec2
    product = to_pauli_str(vec_product)

    op_pair = (('X', 'Y'), ('Y', 'Z'), ('Z', 'X'))
    phase = 1.0
    for op1, op2 in zip(word1, word2):
        if op1 == 'I' or op2 == 'I' or op1 == op2:
            continue
        if (op1, op2) in op_pair:
            phase *= 1j
        else:
            phase *= -1j
    return product, phase

def multiply_hamiltonian(ham1: List, ham2: List):
    len1 = len(ham1)
    len2 = len(ham2)
    result = []
    for i in range(len1):
        for j in range(len2):
            product, phase = multiply_pauli_str(ham1[i][0], ham2[j][0])
            coeff = phase * ham1[i][1] * ham2[j][1]
            result.append((product, coeff))
    return combine_terms(result)
    
def generate_clifford_hamiltonian(generators, xqubits) -> List:
    hams = []
    qnum = len(generators[0][0])
    factor = 1 / 2**0.5
    for i, q in enumerate(xqubits):
        base = ['I']*qnum
        base[q] = 'X'
        hams.append([(''.join(base), factor), (generators[i][0], generators[i][1]*factor)])
    res = functools.reduce(lambda i,j: multiply_hamiltonian(i, j), hams)
    return res

def taper_off_qubits(hamiltonian: List, generators: List, sector: List) -> List:
    qnum = len(hamiltonian[0][0])
    xqubits = generate_X_qubits(generators)
    clifford = generate_clifford_hamiltonian(generators, xqubits)
    ham = multiply_hamiltonian(multiply_hamiltonian(clifford, hamiltonian), clifford)

    signs = np.ones(len(ham), dtype=np.complex64)
    for idx, xq in enumerate(xqubits):
        for i in range(len(ham)):
            s = ham[i][0]
            if s[xq] == 'X':
                signs[i] *= sector[idx]
    
    coeffs = np.array([elem[1] for elem in ham])
    coeffs = np.multiply(signs, coeffs)

    remaining = [q for q in range(qnum) if q not in xqubits]
    ops = []
    for elem in ham:
        word = elem[0]
        ops.append(''.join([word[i] for i in remaining]))

    tapered = [(o, c) for o, c in zip(ops, coeffs)]
    return combine_terms(tapered)
    