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
    """Describe a cloud quantum-computing platform and its capabilities."""

    def __init__(self, code: str, name: str, max_bitnum: int, machine_count: int = 0, gate_list: List[Gate] = [], coupling_map: List[tuple] = None, simu: bool = False, active_qubits: List[int] = None, system: str = None) -> None:
        """Initialize metadata returned by the cloud platform API.

        Last updated: 2026-10-12 - Store the optional platform system type for
        backend-specific result polling.
        Args:
            code (str): Platform identifier.
            name (str): Display name.
            max_bitnum (int): Maximum supported qubit count.
            machine_count (int): Number of online machines.
            gate_list (List[Gate]): Supported gates.
            coupling_map (List[tuple]): Physical connectivity edges.
            simu (bool): Whether this platform is a simulator.
            active_qubits (List[int]): Online physical qubits.
            system (str): Optional cloud-reported system type.
        Returns:
            None: Metadata is stored on this platform instance.
        """
        from datetime import datetime
        self._code = code
        self._name = name
        self._max_bitnum = max_bitnum
        self._machine_count = machine_count
        self._support_gates = gate_list
        self._simu = simu
        self._coupling_map = coupling_map
        self._active_qubits = active_qubits
        self._system = system
        self._latest_updated_time = datetime.now()

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

    @property
    def simu(self) -> bool:
        return self._simu

    @property
    def system(self) -> str:
        """Return the optional cloud-reported platform system type.

        Last updated: 2026-10-12 - Expose the system type used for polling.
        Args:
            None.
        Returns:
            str: System identifier, such as ``nmr``, or ``None`` when absent.
        """
        return self._system

    def available(self) -> bool:
        return self._machine_count > 0

    def has_gate(self, g: Gate) -> bool:
        for x in self._support_gates:
            if x.gname == g.gname: return True
        return False

    @property
    def coupling_map(self) -> List:
        return self._coupling_map
    
    @property
    def active_qubits(self) -> List:
        return self._active_qubits
    
    @property
    def latest_updated_time(self):
        return self._latest_updated_time

    def __str__(self) -> str:
        p_dict = {}
        p_dict["code"] = self._code
        p_dict["name"] = self._name
        p_dict["simu"] = self._simu
        p_dict["max_bitnum"] = self._max_bitnum
        p_dict["machine_count"] = self._machine_count
        p_dict["support_gates"] = [g.to_dict() for g in self._support_gates]
        p_dict["coupling_map"] = self._coupling_map
        return json.dumps(p_dict)

Gemini = Platform("gemini_vp", None, 2)
Triangulum = Platform("triangulum_vp", None, 3)
Superconductor = Platform("superconductor_vp", None, 8)
SQC_25 = Platform("sqc_25_vp", None, 25)
Simu_25 = Platform("simulator", None, 25)
