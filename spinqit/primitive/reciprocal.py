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
import numpy as np
from spinqit.model import Instruction
from spinqit.compiler.decomposer import generate_uc_rot_gates

class Reciprocal(object):
    def __init__(self, qubits: List, delta: float):
        self.__qubits = qubits
        self.__angles = [0.0]
        nl = 2 ** (len(qubits) - 1)
        
        for i in range(1, nl):
            if np.isclose(delta * nl / i, 1, atol=1e-5):
                self.__angles.append(np.pi)
            elif delta * nl / i < 1:
                self.__angles.append(2 * np.arcsin(delta * nl / i))
            else:
                self.__angles.append(0.0)

    def build(self) -> List[Instruction]:
        uc_rot = generate_uc_rot_gates(self.__angles, 'y')
        return [Instruction(uc_rot, self.__qubits)]