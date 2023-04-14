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
from typing import List
import math
import numpy as np

from spinqit.model import Gate, GateBuilder, ControlledGate
from spinqit.model import Rx, Ry, Rz, CX, I

_EPS = 1e-10

def update_angles(angles: List, idx0: int, idx1: int, reverse: bool):
    angle0 = angles[idx0]
    angle1 = angles[idx1]
    if not reverse:
        angles[idx0] = (angle0 + angle1) / 2.0
        angles[idx1] = (angle0 - angle1) / 2.0
    else:
        angles[idx1] = (angle0 + angle1) / 2.0
        angles[idx0] = (angle0 - angle1) / 2.0

def calculate_rotations(angles: List, beg: int, end: int, reverse: bool):
    mid = (end - beg) // 2
    for i in range(beg, beg + mid):
        update_angles(angles, i, i+mid, reverse)
    if mid <= 1:
        return
    else:
        calculate_rotations(angles, beg, beg+mid, False)
        calculate_rotations(angles, beg+mid, end, True)

def generate_uc_rot_gates(angles: List, axis: str) -> Gate:
    ctrl_num = math.log2(len(angles))
    if ctrl_num < 0 or not ctrl_num.is_integer():
        raise ValueError('The size of angles should be power of 2.')
    qubit_num = int(ctrl_num) + 1

    uc_rot_builder = GateBuilder(qubit_num)
    q_target = 0
    q_controls = list(range(1, qubit_num))

    axis = axis.lower()
    if axis not in ('x', 'y', 'z'):
        raise ValueError
    if axis == 'x':
        rot_gate = Rx
    elif axis == 'y':
        rot_gate = Ry
    else:
        rot_gate = Rz

    if qubit_num == 1:
        if np.abs(angles[0]) > _EPS:
            uc_rot_builder.append(rot_gate, [q_target], angles[0])
    else:
        calculate_rotations(angles, 0, len(angles), False)
        for (i, angle) in enumerate(angles):
            if np.abs(angle) > _EPS:
                uc_rot_builder.append(rot_gate, [q_target], angle)
            if i != len(angles) - 1:
                bi_str = np.binary_repr(i + 1)
                ctrl_idx = len(bi_str) - len(bi_str.rstrip('0'))
            else:
                ctrl_idx = len(q_controls) - 1
            if axis == 'x':
                uc_rot_builder.append(Ry, [q_target], np.pi/2)
            uc_rot_builder.append(CX, [q_controls[ctrl_idx], q_target])
            if axis == 'x':
                uc_rot_builder.append(Ry, [q_target], np.pi/2)
    if uc_rot_builder.size() == 0:
        uc_rot_builder.append(I, [q_target])
    return uc_rot_builder.to_gate()

