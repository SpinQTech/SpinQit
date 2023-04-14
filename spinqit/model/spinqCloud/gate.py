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

class Gate:
    def __init__(self, name: str, tag: str):
        self._gname = name
        self._gtag = tag

    @property
    def gtag(self):
        return self._gtag

    @property
    def gname(self):
        return self._gname

    def to_dict(self):
        gate_dict = {"gname": self._gname, "gtag": self._gtag}
        return gate_dict

H = Gate('H', "C1")
I = Gate('I', "C1")
X = Gate('X', "C1")
Y = Gate('Y', "C1")
Z = Gate('Z', "C1")
X90 = Gate('X90', "C1")
Y90 = Gate('Y90', "C1")
Z90 = Gate('Z90', "C1")
X90dg = Gate('X90dg', "C1")
Y90dg = Gate('Y90dg', "C1")
Z90dg = Gate('Z90dg', "C1")
Rx = Gate('Rx', "R1")
Ry = Gate('Ry', "R1")
Rz = Gate('Rz', "R1")
CNOT = Gate('CNOT', "C2")
YCON = Gate('YCON', "C2")
ZCON = Gate('ZCON', "C2")
T = Gate('T', "C1")
Td = Gate('Td', "C1")
S = Gate('S', "C1")
Sd = Gate('Sd', "C1")
CCX = Gate('CCNOT', "C3")
Measure = Gate('Measure', "Measure")
Barrier = Gate('Barrier', "Barrier")
U = Gate('U', "U1")
base_gate_list = [H, I, X, Y, Z, X90, Y90, Z90, X90dg, Y90dg, Z90dg, Rx, Ry, Rz, CNOT, YCON, ZCON, T, Td, S, Sd, CCX, Measure, Barrier, U]

def find_gate(gname: str):
    for g in base_gate_list:
        if g.gname == gname: return g
    return None