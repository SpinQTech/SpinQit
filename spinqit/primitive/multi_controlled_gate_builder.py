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
from typing import Union
import numpy as np

from spinqit.model import CNOT, CCX, P, X, Rz, Ry, Ph
from spinqit.compiler.decomposer import decompose_zyz
from spinqit.model import Gate, GateBuilder

class MultiControlledGateBuilder(GateBuilder):
    """
    Construct Multi Controlled Gate (MCG) using quantum multiplexor method.

    For more details, see article:
        1. Barenco, Bennett et al. Elementary gates for quantum computation. 1995. https://arxiv.org/pdf/quant-ph/9503016.pdf
    """

    def __init__(self, ctrl_num: int, gate: Union[Gate, np.ndarray, list], params=None):
        super().__init__(ctrl_num + 1)
        if gate.qubit_num > 1:
            raise ValueError('The MCG only support single qubit gate')
        if isinstance(gate, Gate):
            mat = gate.get_matrix(params)
        elif isinstance(gate, list):
            mat = np.array(gate)
        else:
            mat = gate

        self.gate_mat = mat
        gate_list = self.decompose(self.gate_mat, controls=list(range(ctrl_num)), target=ctrl_num)
        for x in gate_list:
            self.append(*x)

    def decompose(self, matrix, controls, target):
        assert np.allclose(matrix.T.conj() @ matrix, np.eye(2))
        assert matrix.shape == (2, 2)
        m = len(controls)

        if m == 0:
            return self.single_qubit_gate(matrix, target)
        elif m == 1:
            return self._decompose_single_ctrl(matrix, controls[0], target)
        elif self.is_special_unitary(matrix):
            return self._decompose_su(matrix, controls, target)
        else:
            return self._decompose_recursive(matrix, 1.0, controls, target, [])

    def _ccnot(self, c0, c1, target, congurent=False):
        if congurent:
            return [(Ry, [target], -np.pi / 4),
                    (CNOT, [c1, target]),
                    (Ry, [target], -np.pi / 4),
                    (CNOT, [c0, target]),
                    (Ry, [target], np.pi / 4),
                    (CNOT, [c1, target]),
                    (Ry, [target], np.pi / 4)]
        return [(CCX, [c0, c1, target])]

    def _multi_ctrl_x(self, controls, target, free_qubits):
        # control num
        m = len(controls)

        if m == 0:
            return [(X, [target])]
        elif m == 1:
            return [(CNOT, controls + [target])]
        elif m == 2:
            return [(CCX, controls + [target])]
        else:
            # qubit_num
            n = m + 1 + len(free_qubits)

            if (n >= 2 * m - 1) and (m >= 3):
                first_ccnot = self._ccnot(controls[m - 1],
                                          free_qubits[m - 3],
                                          target)
                gates1 = []
                for i in range(m - 3):
                    gates1.extend(self._ccnot(controls[m - 2 - i],
                                              free_qubits[m - 4 - i],
                                              free_qubits[m - 3 - i]))
                gates2 = self._ccnot(controls[0],
                                     controls[1],
                                     free_qubits[0], )
                gates3 = gates1 + gates2 + gates1[::-1]

                return first_ccnot + gates3 + first_ccnot + gates3
            elif len(free_qubits) >= 1:
                # See [1], Lemma 7.3.
                m1 = n // 2
                free1 = controls[m1:] + [target] + free_qubits[1:]
                ctrl1 = controls[:m1]
                free2 = controls[:m1] + free_qubits[1:]
                ctrl2 = controls[m1:] + [free_qubits[0]]
                part1 = self._multi_ctrl_x(ctrl1, free_qubits[0], free_qubits=free1)
                part2 = self._multi_ctrl_x(ctrl2, target, free_qubits=free2)
                return part1 + part2 + part1 + part2
            else:
                # No free qubit - must use main algorithm.
                # This will never happen if called from main algorithm and is added
                # only for completeness.
                self.decompose(X.get_matrix(), controls, target)

    def _decompose_recursive(self, matrix, power, ctrl, target, free_qubits):
        """
        see [1], lemma 7.5
        """
        if len(ctrl) == 1:
            return self._decompose_single_ctrl(self._unitary_power(matrix, power), ctrl[0], target)
        _cnots = self._multi_ctrl_x(ctrl[:-1], ctrl[-1], free_qubits=free_qubits + [target])
        return (self._decompose_single_ctrl(self._unitary_power(matrix, 0.5 * power), ctrl[-1], target) +
                _cnots +
                self._decompose_single_ctrl(self._unitary_power(matrix, -0.5 * power), ctrl[-1], target) +
                _cnots +
                self._decompose_recursive(matrix, 0.5 * power, ctrl[:-1], target, [ctrl[-1]] + free_qubits))

    def _decompose_single_ctrl(self, matrix, ctrl, target):
        """
        See [1], chapter 5.1.
        """
        beta, theta, alpha, delta = decompose_zyz(matrix)
        return [(Rz, [target], 0.5 * (beta - alpha)),
                (CNOT, [ctrl] + [target]),
                (Rz, [target], -0.5 * (beta + alpha)),
                (Ry, [target], -0.5 * theta),
                (CNOT, [ctrl] + [target]),
                (P, [ctrl], delta),
                (Ry, [target], 0.5 * theta),
                (Rz, [target], alpha)]

    def _decompose_su(self, matrix, ctrl, target):
        """
        see [1] lemma 7.9
        """
        A, B, C = self._decompose_abc(matrix)
        _cnots = self._multi_ctrl_x(ctrl[:-1], target, free_qubits=[ctrl[-1]])
        return (
                self._decompose_single_ctrl(C, ctrl[-1], target) +
                _cnots +
                self._decompose_single_ctrl(B, ctrl[-1], target) +
                _cnots +
                self._decompose_single_ctrl(A, ctrl[-1], target)
        )

    @staticmethod
    def single_qubit_gate(matrix, target):
        beta, theta, alpha, delta = decompose_zyz(matrix)
        inst_list = [(Rz, target, beta),
                     (Ry, target, theta),
                     (Rz, target, alpha), ]
        if abs(delta) > 1e-6:
            inst_list.append((Ph, target, delta))
        return inst_list

    @staticmethod
    def _decompose_abc(matrix):
        beta, theta, alpha, delta = decompose_zyz(matrix)
        A = Rz.get_matrix(alpha) @ Ry.get_matrix(theta / 2)
        B = Ry.get_matrix(-theta / 2) @ Rz.get_matrix(-(alpha + beta) / 2)
        C = Rz.get_matrix((beta - alpha) / 2)
        if not np.allclose(A @ B @ C, np.eye(2), atol=1e-4):
            print('alpha', alpha)
            print('beta', beta)
            print('theta', theta)
            print('delta', delta)
            print('A', A)
            print('B', B)
            print('C', C)
            print(np.abs(A @ B @ C))
        assert np.allclose(A @ B @ C, np.eye(2), atol=1e-2)
        assert np.allclose(
            A @ X.get_matrix() @ B @ X.get_matrix() @ C,
            matrix /
            np.exp(
                1j *
                delta),
            atol=1e-2)
        return A, B, C

    @staticmethod
    def _unitary_power(U, p):
        """Raises unitary matrix U to power p."""
        eig_vals, Q = np.linalg.eig(U)
        return Q @ np.diag(np.exp(p * 1j * np.angle(eig_vals))) @ Q.conj().T

    @staticmethod
    def is_special_unitary(matrix):
        beta, theta, alpha, delta = decompose_zyz(matrix)
        return np.allclose(delta, 0.)