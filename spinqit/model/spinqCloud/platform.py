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
from .gate import *
import json

class Platform():
    def __init__(self, code: str, name: str, max_bitnum: int, machine_count: int, gate_list: List[Gate] = [], coupling_map: List[tuple] = None) -> None:
        self._code = code
        self._name = name
        self._max_bitnum = max_bitnum
        self._machine_count = machine_count
        self._support_gates = gate_list
        self._coupling_map = coupling_map

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def max_bitnum(self) -> int:
        return self._max_bitnum

    @property
    def machine_count(self) -> int:
        return self._machine_count

    def available(self) -> bool:
        return self._machine_count > 0

    def has_gate(self, g: Gate) -> bool:
        for x in self._support_gates:
            if x.gname == g.gname: return True
        return False

    @property
    def coupling_map(self) -> List:
        return self._coupling_map

    def __str__(self) -> str:
        p_dict = {}
        p_dict["code"] = self._code
        p_dict["name"] = self._name
        p_dict["max_bitnum"] = self._max_bitnum
        p_dict["machine_count"] = self._machine_count
        p_dict["support_gates"] = [g.to_dict() for g in self._support_gates]
        p_dict["coupling_map"] = self._coupling_map
        return json.dumps(p_dict)

Gemini = Platform("gemini_vp", "2Qubit小型核磁量子计算机", 2, 0, [H, I, X, Y, Z, X90, Y90, Z90, Rx, Ry, Rz, CNOT, YCON, ZCON, Barrier, U], [(1, 2), (2, 1)])
Triangulum = Platform("triangulum_vp", "3Qubit核磁量子计算机", 3, 0, [H, I, X, Y, Z, U, Rx, Ry, Rz, T, Td, X90, Y90, Z90, Barrier, CNOT, ZCON, CCX], [(1, 2), (2, 1), (2, 3), (3, 2), (3, 1), (1, 3)])
Superconductor = Platform("superconductor_vp", "8Qubit超导量子计算机", 8, 0, [H, X, Y, Z, X90, Y90, Z90, Rx, Ry, Rz, ZCON, T, S, Barrier, X90dg, Y90dg, Z90dg, I, U], [(1, 2), (2, 1), (2, 3), (3, 2), (3, 4), (4, 3), (4, 5), (5, 4), (5, 6), (6, 5), (6, 7), (7, 6), (7, 8), (8, 7)])

def find_platform(pcode):
    for p in [Gemini, Triangulum, Superconductor]:
        if p.code == pcode: return p
    return None