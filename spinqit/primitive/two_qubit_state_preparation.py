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
from spinqit import GateBuilder, Ry, Rz, CZ
from spinqit.compiler.decomposer import decompose_zyz
import numpy as np

_EPS = 1e-10

def _unitary_matrix(x, y):
    coeff = 1 / np.linalg.norm([x, y], 2)
    mat = np.array([[x, y], [-y.conjugate(), x.conjugate()]], dtype=complex)
    return coeff * mat

class TwoQubitStatePreparationGateBuilder(GateBuilder):
    """
    Arbitrary 2-qubit state preparation
    This class supports both density matrix and state vector

    For more details, see the article:
        1. scar Perdomo, Nelson Castaneda, and Roger Vogeler.
           Preparation of 3-qubit states. arXiv preprint arXiv:2201.03724, 2022.
    """

    def __init__(self, state: np.ndarray):
        if len(state.shape) == 1:
            state = np.kron(state.reshape(-1, 1), state.conjugate())
        qubit_num = int(np.log2(state.shape[0]))
        if qubit_num != 2:
            raise ValueError('Only Supported 2-qubit state')
        purity = np.trace(state @ state)
        if abs(abs(purity) - 1) > 1e-6:
            raise ValueError('The state should be pure state.')
        super().__init__(qubit_num)

        # Get the w1 matrix
        eigval, eigvec = np.linalg.eig(state)
        s = (abs(eigval) - 0.0) > _EPS
        u = eigvec.T
        state = np.select(s, u)
        a0, a1, a2, a3 = state
        A1 = np.array([a0, a1])
        A2 = np.array([a2, a3])
        A1_norm = np.linalg.norm(A1)
        A2_norm = np.linalg.norm(A2)
        inner_product = (A2 @ A1.reshape(-1, 1).conjugate())[0]
        if abs(inner_product - 0.0) < _EPS:
            k = (A2_norm / A1_norm)
        else:
            k = -(A2_norm / A1_norm) * (
                    inner_product / abs(inner_product))
        w1 = _unitary_matrix(a3 - k * a1, a2.conjugate() - k.conjugate() * a0.conjugate()).T

        # Get the w2 matrix
        czmat = CZ.get_matrix()
        i_w1 = np.kron(np.identity(2), w1)
        state = czmat @ i_w1 @ state
        b0, b1, b2, b3 = state
        w2 = _unitary_matrix(b1.conjugate(), b3.conjugate())

        # Get the w3 matrix
        w2_i = np.kron(w2, np.identity(2))
        state = w2_i @ state
        g0, g1, g2, g3 = state
        w3 = _unitary_matrix(g0.conjugate(), -g1.conjugate()).T

        # Construct the gatebuilder
        def add_arbitrary_single_qubit_gate(mat, target):
            alpha, beta, gamma, phase = decompose_zyz(mat)
            if abs(alpha) > _EPS:
                self.append(Rz, [target], alpha)
            if abs(beta) > _EPS:
                self.append(Ry, [target], beta)
            if abs(gamma) > _EPS:
                self.append(Rz, [target], gamma)

            if abs(phase) > _EPS:
                self.append(Ph, [target], phase)

        add_arbitrary_single_qubit_gate(w2.conjugate().T, 0)
        add_arbitrary_single_qubit_gate(w3.conjugate().T, 1)
        self.append(CZ, [0, 1])
        add_arbitrary_single_qubit_gate(w1.conjugate().T, 1)
