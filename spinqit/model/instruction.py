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

from typing import List, Tuple, Union
from .basic_gate import Gate
import numpy as np
from .parameter import LazyParameter
from spinqit.utils.function import to_list


class Instruction(object):
    def __init__(self, gate: Gate, qubits=[], clbits=[], *params: Tuple):
        self.gate = gate
        self.qubits = qubits
        self.clbits = clbits

        params = to_list(params)
        self.params = params
        if len(params) == 1:
            if params[0] is None:
                self.params = []
            # elif isinstance(params[0], LazyParameter):
            #     self.params = params[0]
        
        self.condition = None

        if len(qubits) != gate.qubit_num and gate.label not in ['MEASURE', 'BARRIER', 'StateVector']:
            raise ValueError('The number of qubits does not match the gate.')

    def set_condition(self, clbits: Union[List, int], symbol: str, constant: int):
        if isinstance(clbits, int):
            clbits = [clbits]
        self.condition = (clbits, symbol, constant)

    def get_op(self) -> str:
        return self.gate.label

    def __repr__(self):
        return (
            f'Instruction('
            f'gate:{self.gate.label}, '
            f'qubits:{self.qubits}, '
            f'clbits:{self.clbits}, '
            f'params:{self.params})'
        )

    def __str__(self):
        return (
            f'Instruction('
            f'gate:{self.gate.label}, '
            f'qubits:{self.qubits}, '
            f'clbits:{self.clbits}, '
            f'params:{self.params})'
        )
