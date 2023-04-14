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
from spinqit.model import Gate, GateBuilder
from .uniformly_controlled_rotation_gate import generate_uc_rot_gates

def generate_diagonal_gates(diag: Union[List, np.ndarray]) -> Gate:
    """
    Using Rotation type gate to construct the diagonal gates.

    Notes:
        For now, the gate is still lost phase

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

        previous_act = int(np.log2(n))
        control_indexes = list(range(qnum - previous_act + 1, qnum))
        control_qubits = [q for q in control_indexes]
        target_qubit = qnum - previous_act
        uc_rot = generate_uc_rot_gates(angles_rz, 'z')
        diag_builder.append(uc_rot, [target_qubit] + control_qubits)
        n //= 2

    return diag_builder.to_gate()
