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
from typing import List, Any
import numpy as np
import scipy.linalg
from spinqit import get_compiler
from spinqit.model import Circuit, X, Z, Ry, CX, MatrixGateBuilder
from spinqit.compiler.decomposer import generate_uc_rot_gates
# from spinqit.model.basic_gate import GateBuilder
from spinqit.primitive import PhaseEstimation, amplitude_encoding, Reciprocal

xmat = X.get_matrix()
zmat = Z.get_matrix()

class HHL(object):
    def __init__(self, mat_A: np.ndarray, vec_b: np.ndarray):
        if mat_A.shape[0] != mat_A.shape[1]:
            raise ValueError('The matrix must be square.')
        if not np.log2(mat_A.shape[0]).is_integer():
            raise ValueError('The matrix dimension must be power of 2.')
        if not np.allclose(mat_A, mat_A.conj().T):
            raise ValueError('The matrix must be hermitian.')
        if mat_A.shape[0] != len(vec_b):
            raise ValueError('The matrix dimension must match the vector dimension.')

        self.__mat_A = mat_A
        self.__vec_b = vec_b
        self.__circuit = self._build()

    def _build(self) -> Circuit:
        vq_num = int(np.log2(len(self.__vec_b)))
        condition_num = np.linalg.cond(self.__mat_A)
        mq_num = max(vq_num+1, int(np.log2(condition_num)) + 1)
        
        eigvals = np.abs(np.linalg.eigvals(self.__mat_A))
        delta = self._get_delta(mq_num, min(eigvals), max(eigvals))
        evolution_time = 2 * np.pi * delta / min(eigvals)

        # When delta > 0.25, the first two angles in ucrot would be 0
        if mq_num == 2 and delta > 0.25:
            mq_num = 1

        circ = Circuit()
        
        qb = circ.allocateQubits(vq_num)
        qe = circ.allocateQubits(mq_num)
        qf = circ.allocateQubits(1)

        vector_encoding = amplitude_encoding(self.__vec_b, qb)
        circ.extend(vector_encoding)

        if mq_num == 1:
            a = np.trace(np.dot(xmat, self.__mat_A)) / 2.0
            b = np.trace(np.dot(zmat, self.__mat_A)) / 2.0
            theta = np.arctan(b/a) - np.pi/2

            circ << (Ry, qb, theta)
            circ << (CX, qb + qe)
            
            angles = []
            for i in range(2, 4):
                if np.isclose(delta * 4 / i, 1, atol=1e-5):
                    angles.append(np.pi)
                elif delta * 4 / i < 1:
                    angles.append(2 * np.arcsin(delta * 4 / i))
                else:
                    angles.append(0.0)
            uc_rot = generate_uc_rot_gates(angles, 'y')
            circ << (uc_rot, qf+qe)

            circ << (CX, qb + qe)
            circ << (Ry, qb, -1 * theta)

            return circ

        unitary = self._generate_unitary_for_matrix(evolution_time)
        matrix_gate = MatrixGateBuilder(unitary).to_gate()
        # matrix_gate_builder = GateBuilder(1)
        # matrix_gate_builder.set_matrix(lambda *args: unitary)
        # matrix_gate = matrix_gate_builder.to_gate()
        
        qpe = PhaseEstimation(matrix_gate, qb, qe)
        circ.extend(qpe.build())

        reciprocal = Reciprocal(qf+qe[::-1], delta).build()
        circ.extend(reciprocal)

        circ.extend(qpe.inverse())
        return circ
       
    def _get_delta(self, nl: int, eig_min: float, eig_max: float):
        min_tilde = np.abs(eig_min * (2 ** nl - 1) / eig_max)
        if np.abs(min_tilde - 1) < 1e-7:
            min_tilde = 1
        min_tilde = int(min_tilde)
        min_rep = 0.0
        for i in range(nl):
            min_rep += ((min_tilde >> i) & 1) / (2 ** (nl - i))
        return min_rep

    def _generate_unitary_for_matrix(self, evolution_time: float):
        return scipy.linalg.expm(1j * self.__mat_A * evolution_time)

    def get_circuit(self):
        return self.__circuit

    def run(self, backend: Any, config: Any):
        compiler = get_compiler("native")
        optimization_level = 1
        exe = compiler.compile(self.__circuit, optimization_level)
        # exe.plot_dag(save_path="hhl.png", bbox=(1500, 1500))
        self.result = backend.execute(exe, config)

    def get_state(self):
        return self.result.states

    def get_measurements(self):
        return self.result.probabilities