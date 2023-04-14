# Copyright 2022 SpinQ Technology Co., Ltd.
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
from typing import Union
import numpy as np

from spinqit.model import Gate, GateBuilder
from spinqit.compiler.decomposer import generate_ucg_diagonal

class UniformlyControlledGateBuilder(GateBuilder):
    """
    Construct uniformly controlled gate (UCG) using quantum multiplexor method.

    Examples:
        1.
            qubit_num = 1
            gate = X
            ucg_gatebuilder = UniformlyControlledGateBuilder(qubit_num, gate)
            ucg_gate = ucg_gatebuilder.to_gate()


        2.
            qubit_num = 1
            gate = Rz.matrix([np.pi/2])
            ucg_gatebuilder = UniformlyControlledGateBuilder(qubit_num, gate,)
            ucg_gate = ucg_gatebuilder.to_gate()

        3.
            qubit_num = 1
            gate = Rz
            ucg_gatebuilder = UniformlyControlledGateBuilder(qubit_num, gate, params=pi/2)
            ucg_gate = ucg_gatebuilder.to_gate()
    """

    def __init__(self, ctrl_num: int, gate: Union[Gate, np.ndarray, list], params=None, up_to_diag=False,
                 add_phase=True):
        super().__init__(ctrl_num + 1)
        if gate.qubit_num > 1:
            raise ValueError('The UCG only support single qubit gate')
        if isinstance(gate, Gate):
            if params is not None:
                mat = gate.get_matrix(params)
            else:
                mat = gate.get_matrix()
        elif isinstance(gate, list):
            mat = np.array(gate)
        else:
            mat = gate
        unitary_list = [mat for _ in range(2 ** ctrl_num)]
        ucg_gate, diag = generate_ucg_diagonal(unitary_list, up_to_diag, add_phase)
        self.append(ucg_gate, list(reversed(range(ctrl_num + 1))))
        self.ucg_gate = ucg_gate
        self.diag = diag
