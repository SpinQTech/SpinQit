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
from spinqit.model.instruction import Instruction
from typing import List
from math import pi
from spinqit.model import Gate, RepeatBuilder, InverseBuilder
from spinqit.model import H
from .qft import QFT
from .power import generate_power_gate

class PhaseEstimation(object):
    def __init__(self, unitary: Gate, state_qubits: List, output_qubits: List, params: List = []):
        self.__unitary = unitary
        self.__state_qubits = state_qubits
        self.__output_qubits = output_qubits
        self.__params = params
        
    def build(self) -> List[Instruction]:
        inst_list = []
        h_builder = RepeatBuilder(H, len(self.__output_qubits))
        inst_list.append(Instruction(h_builder.to_gate(), self.__output_qubits))

        qnum = len(self.__output_qubits)
        for i in range(qnum):
            ctrl_power = generate_power_gate(self.__unitary, 2 ** (qnum - i - 1), self.__state_qubits, self.__params, control=True, control_bit=self.__output_qubits[i])
            inst_list.extend(ctrl_power)

        iqft = QFT(len(self.__output_qubits))
        inst_list.append(Instruction(iqft.inverse(), self.__output_qubits))
        
        return inst_list

    def inverse(self) -> List[Instruction]:
        inv_list = []
        inst_list = self.build()
        for inst in reversed(inst_list):
            inv_gate = InverseBuilder(inst.gate).to_gate()
            inv_list.append(Instruction(inv_gate, inst.qubits, inst.clbits, *inst.params))
        return inv_list
        

        