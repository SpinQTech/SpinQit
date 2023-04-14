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

from spinqit.model.gates import X,CX,CCX
from typing import List
import numpy as np
from .basic_gate import Gate
from .controlled_gate_decomposer import control_basis_decomposition

class ControlledGate(Gate):
    def __init__(self, gate: Gate):    
        self.__qubit_num = 1 + gate.qubit_num
        self.subgate = gate
        self.control_bits = 1
        if isinstance(gate, ControlledGate):
            self.control_bits += gate.control_bits
            self.__label = 'C' + str(self.control_bits) + gate.label
            self.base_gate = gate.base_gate
        else:
            self.__label = 'C' + gate.label
            self.base_gate = gate
        
        self.__matrix = None
        self.__factors = []
        sub_factors = self.subgate.factors
        if len(sub_factors) > 0:
            for f in sub_factors:
                if f[0] == X:
                    gate = CX
                elif f[0] == CX:
                    gate = CCX
                else:
                    gate = ControlledGate(f[0])
                qubits = [0]
                qubits.extend([i+1 for i in f[1]])
                if len(f) > 2:
                    params = f[2]
                    self.__factors.append((gate, qubits, params))
                else:
                    self.__factors.append((gate, qubits))
        else:
            qubits = list(range(self.__qubit_num))
            factors = control_basis_decomposition(self.subgate, qubits)
            self.__factors = factors

    @property
    def label(self) -> str:
        return self.__label

    @property
    def qubit_num(self):
        return self.__qubit_num

    @property
    def factors(self) -> List:
        return self.__factors

    def get_matrix(self, *params):
        m = self.subgate.get_matrix(*params)
        if m is None:
            return None
        m0 = np.zeros(len(m))
        m1 = np.eye(len(m))
        m10 = np.concatenate([m1, m0], axis=1)
        m = np.concatenate([m0, m], axis=1)
        m = np.concatenate([m10, m], axis=0)

        return m

