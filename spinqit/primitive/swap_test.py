# Copyright 2024 SpinQ Technology Co., Ltd.
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
from .vector_encoding import amplitude_encoding
from ..model import Instruction, H, CSWAP

class SwapTest():
    def __init__(self, state1: np.ndarray, state2: np.ndarray, test_qubit: int, squbits1: List[int], squbits2: List[int]):
        if state1.ndim != 1 and not (state1.ndim == 2 and state1.shape[1] == 1):
            raise ValueError('The shape of state1 is not correct.')
        if state2.ndim != 1 and not (state2.ndim == 2 and state2.shape[1] == 1):
            raise ValueError('The shape of state2 is not correct.')
        if len(state1) != len(state2):
            raise ValueError('The two states do not have the same size.')
        if len(squbits1) != len(squbits2):
            raise ValueError('The two qubit lists do not have the same size.')
        squbit_num = int(np.log2(len(state1)))
        if squbit_num != len(squbits1):
            raise ValueError('The number of qubits does not match the size of state.')
        
        self.state1 = state1
        self.state2 = state2
        self.test_qubit = test_qubit
        self.squbits1 = squbits1
        self.squbits2 = squbits2

    def build(self) -> List[Instruction]:
        inst_list = []
        inst_list.extend(amplitude_encoding(self.state1, self.squbits1))
        inst_list.extend(amplitude_encoding(self.state2, self.squbits2))
        inst_list.append(Instruction(H, [self.test_qubit], []))
        for i in range(len(self.squbits1)):
            inst_list.append(Instruction(CSWAP, [self.test_qubit, self.squbits1[i], self.squbits2[i]], []))
        inst_list.append(Instruction(H, [self.test_qubit], []))
        return inst_list

