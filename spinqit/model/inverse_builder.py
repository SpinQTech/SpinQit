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
from .basic_gate import Gate
from .matrix_gate import MatrixGate
from .controlled_gate import ControlledGate
from .gates import I, H, X, Y, Z, Rx, Ry, Rz, P, T, Td, S, Sd, CX, CY, CZ, SWAP, MEASURE, BARRIER
class InverseGate(Gate):
    def __init__(self, gate: Gate) -> None:
        super().__init__(gate.label+'_inv', gate.qubit_num)
        if isinstance(gate, ControlledGate) or isinstance(gate, InverseGate):
            self.sub_gate = gate
            self.base_gate = gate.base_gate
        else:
            self.sub_gate = gate
            self.base_gate = gate

class InverseBuilder(object):
    def __init__(self, gate: Gate) -> None:
        self.__gate = gate

    def to_gate(self) -> Gate:
        return self._inverse(self.__gate)
        
    def _inverse(self, g: Gate) -> Gate:
        if g in (I, H, X, Y, Z, CX, CY, CZ, SWAP, MEASURE, BARRIER):
            return g
        elif g in (Rx, Ry, Rz, P):
            rot_gate = InverseGate(g)
            param_lambda = lambda params: -1 * params[0]
            rot_gate.factors.append((g, list(range(g.qubit_num)), param_lambda))
            return rot_gate
        elif g == T:
            return Td
        elif g == Td:
            return T
        elif g == S:
            return Sd
        elif g == Sd:
            return S
        elif len(g.factors) > 0:
            inv_gate = InverseGate(g)
            for f in g.factors:
                if len(f) == 2:
                    inv_gate.factors.append((self._inverse(f[0]), f[1]))
                else:
                    inv_gate.factors.append((self._inverse(f[0]), f[1], f[2]))
            inv_gate.factors.reverse()
            return inv_gate