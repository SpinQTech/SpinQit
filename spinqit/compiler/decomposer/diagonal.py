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
from spinqit.model import Gate, GateBuilder, Ph
from .uniformly_controlled_rotation_gate import generate_uc_rot_gates

def generate_diagonal_gates(diag: Union[List, np.ndarray]) -> Gate:
    """
    Construct a diagonal gate in big-endian computational basis order.

    Preserve the global phase: it becomes a relative phase when this gate
    is controlled, as in quantum phase estimation.

    """
    qnum = int(np.log2(len(diag)))
    diag_builder = GateBuilder(qnum)
    diag_phases = [cmath.phase(z) for z in diag]

    n = len(diag)
    while n >= 2:
        angles_rz = []
        for i in range(0, n, 2):
            z_angle = diag_phases[i + 1] - diag_phases[i] 
            diag_phases[i // 2] = (diag_phases[i] + diag_phases[i + 1]) / 2.0
            angles_rz.append(z_angle)

        target_qubit = int(np.log2(n)) - 1
        # Uniformly controlled rotations take the least significant control
        # first, whereas matrix rows have qubit 0 most significant.
        control_qubits = list(range(target_qubit - 1, -1, -1))
        uc_rot = generate_uc_rot_gates(angles_rz, 'z')
        diag_builder.append(uc_rot, [target_qubit] + control_qubits)
        n //= 2

    if abs(diag_phases[0]) > 1e-10:
        diag_builder.append(Ph, [0], diag_phases[0])

    return diag_builder.to_gate()
