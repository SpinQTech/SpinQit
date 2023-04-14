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
from math import pi
from spinqit.model import Gate, Instruction
from spinqit.model import H, X, Z
from spinqit.model import RepeatBuilder, InverseBuilder
from .multi_controlled_gate_builder import MultiControlledGateBuilder

class AmplitudeAmplification(object):
    def __init__(self, flip: Gate, flip_qubits: List, flip_params: List = [], 
                state_operator: Gate = None, state_qubits: List = [], state_params: List = [],
                reflection_qubits: List = None):
        self.__flip = flip
        self.__flip_qubits = flip_qubits
        self.__flip_params = flip_params
        self.__state_operator = self._state_operator() if state_operator is None else state_operator
        self.__state_qubits = flip_qubits if state_operator is None else state_qubits
        self.__state_params = state_params
        self.__reflection_qubits = flip_qubits if reflection_qubits is None else reflection_qubits

    def _state_operator(self):
        hbuilder = RepeatBuilder(H, self.__flip.qubit_num)
        return hbuilder.to_gate()

    def build(self) -> List[Instruction]:
        inst_list = []
        inst_list.append(Instruction(self.__flip, self.__flip_qubits, [], self.__flip_params))
        
        iBuilder = InverseBuilder(self.__state_operator)
        inst_list.append(Instruction(iBuilder.to_gate(), self.__state_qubits, [], self.__state_params))

        xBuilder = RepeatBuilder(X, len(self.__reflection_qubits))
        inst_list.append(Instruction(xBuilder.to_gate(), self.__reflection_qubits))
        
        if len(self.__reflection_qubits) == 1:
            inst_list.append(Instruction(Z, self.__reflection_qubits[0]))
        else:
            mcz_builder = MultiControlledGateBuilder(len(self.__reflection_qubits) - 1, gate=Z)
            inst_list.append(Instruction(mcz_builder.to_gate(), self.__reflection_qubits, []))
        
        inst_list.append(Instruction(xBuilder.to_gate(), self.__reflection_qubits))
        
        inst_list.append(Instruction(self.__state_operator, self.__state_qubits, [], self.__state_params))
        return inst_list