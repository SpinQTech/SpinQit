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
import cmath
from spinqit.model import GateBuilder, Ry, Rz, Ph
from spinqit.model.Ising_gate import Z_IsingGateBuilder
from .ZYZdecomposer import decompose_zyz
from .diagonal import generate_diagonal_gates

_EPS = 1e-10

def _demultiplex(g0, g1):
    x = g0 @ g1.conjugate().T
    det_x = np.linalg.det(x)
    x11 = x[0, 0] / cmath.sqrt(det_x)
    phi = cmath.phase(det_x)

    # We choose delta = pi/2, k=-1, m=0,
    # k and m are arbitrary integers with k+m odd
    r1 = np.exp(1j / 2 * (-np.pi / 2 - phi / 2 - cmath.phase(x11)))
    r2 = np.exp(1j / 2 * (np.pi / 2 - phi / 2 + cmath.phase(x11)))
    r = np.diag([r1, r2])
    d, u = np.linalg.eig(r @ x @ r)
    if abs(d[0] + 1j) < _EPS:
        d = np.flip(d, 0)
        u = np.flip(u, 1)
    d = np.diag(np.sqrt(d))
    v = d @ u.conjugate().T @ r.conjugate().T @ g1
    return v, u, r, d


def _decompose_ucg(unitary_list: Union[np.ndarray, list], qnum: int):
    gates = [g.astype(complex) for g in unitary_list]
    diag = np.ones(2 ** qnum, dtype=complex)
    ctrls = qnum - 1
    for step in range(ctrls):
        ucg_count = 2 ** step
        for index in range(ucg_count):
            size = 2 ** (ctrls - step)
            for i in range(size // 2):
                delta = index * size
                idx0 = delta + i
                idx1 = delta + i + size // 2
                g0, g1, r, d = _demultiplex(gates[idx0], gates[idx1])
                gates[idx0] = g0
                gates[idx1] = g1
                if index < ucg_count - 1:
                    j = delta + i + size
                    gates[j] = gates[j] @ r.conjugate().T
                    j += size // 2
                    gates[j] = gates[j] @ r
                else:
                    for inner_index in range(ucg_count):
                        inner_delta = inner_index * size
                        ctr = r.conjugate().T
                        j = 2 * (inner_delta + i)
                        diag[j] *= ctr[0, 0]
                        diag[j + 1] *= ctr[1, 1]
                        j += size
                        diag[j] *= r[0, 0]
                        diag[j + 1] *= r[1, 1]

    return gates, diag

def _count_trailing_zero(value: int):
    sz = int(np.log2(value)) + 1
    count = 0
    for i in range(sz):
        if (value>>i) & 1 == 1:
            break
        count += 1
    return count

def generate_ucg_diagonal(unitary_list: List, up_to_diag: bool = False, add_phase: bool = True):
    ctrl_num = int(np.log2(len(unitary_list)))
    qubit_num = ctrl_num + 1

    ucg_builder = GateBuilder(qubit_num)
    if ctrl_num == 0:
        diag = np.ones(2 ** qubit_num).tolist()
        alpha, beta, gamma, phase = decompose_zyz(unitary_list[0])
        if abs(alpha - 0.0) > _EPS:
            ucg_builder.append(Rz, [0], alpha)
        if abs(beta - 0.0) > _EPS:
            ucg_builder.append(Ry, [0], beta)
        if abs(gamma - 0.0) > _EPS:
            ucg_builder.append(Rz, [0], gamma)

        if add_phase:
            if abs(phase) > _EPS:
                ucg_builder.append(Ph, [0], phase)
        return ucg_builder.to_gate(), diag

    sub_gates, diag = _decompose_ucg(unitary_list, qubit_num)
    controls = list(range(1, qubit_num))
    target = 0

    for i in range(len(sub_gates)):
        gate = sub_gates[i]
        umat = gate
        alpha, beta, gamma, phase = decompose_zyz(umat)

        U_gatebuilder = GateBuilder(1)
        if abs(alpha) > _EPS:
            U_gatebuilder.append(Rz, [target], alpha)
        if abs(beta) > _EPS:
            U_gatebuilder.append(Ry, [target], beta)
        if abs(gamma) > _EPS:
            U_gatebuilder.append(Rz, [target], gamma)

        # The global phase
        if add_phase:
            if abs(phase - 0.0) > _EPS:
                U_gatebuilder.append(Ph, [target], phase)
        U_gate = U_gatebuilder.to_gate()
        if U_gate.factors:
            ucg_builder.append(U_gate, [target])

        ctrl_index = _count_trailing_zero(i + 1)
        # The diagonal gate D can be realized using Ising Hamiltonian RZZ(-pi/2)
        D = Z_IsingGateBuilder(2).to_gate()
        if i != len(sub_gates) - 1:
            ucg_builder.append(D, [controls[ctrl_index], target, ], -np.pi / 2)

    if not up_to_diag:
        diag_gate = generate_diagonal_gates(diag)
        ucg_builder.append(diag_gate, list(reversed(range(qubit_num))))

    return ucg_builder.to_gate(), diag


