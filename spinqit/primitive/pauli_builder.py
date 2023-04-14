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
from spinqit.model import GateBuilder, I, X, Y, Z, H, Sd

class PauliBuilder(GateBuilder):
    def __init__(self, pauli_string: str):
        super().__init__(len(pauli_string))
        for i, ch in enumerate(pauli_string):
            if ch.capitalize() == 'X':
                self.append(H, [i])
            elif ch.capitalize() == 'Y':
                self.append(Sd, [i])
                self.append(H, [i])
            elif ch.capitalize() == 'Z' or ch.capitalize() == 'I':
                self.append(I, [i])
            else:
                raise ValueError('The input string is not a Pauli string')
        