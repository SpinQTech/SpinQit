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
from .basic_gate import GateBuilder
from .gates import Rz, CX, H, Rx, Ry
from math import pi


class Z_IsingGateBuilder(GateBuilder):
    def __init__(self, qubit_num: int, name='Z_Ising') -> None:
        super().__init__(qubit_num, name)

        param_lambda = lambda params: params[0]
        if qubit_num == 1:
            self.append(Rz, [qubit_num - 1], param_lambda)
        else:
            for idx in range(qubit_num - 1):
                self.append(CX, [idx, idx + 1])
            self.append(Rz, [qubit_num - 1], param_lambda)
            for idx in range(qubit_num - 1, 0, -1):
                self.append(CX, [idx - 1, idx])


class X_IsingGateBuilder(GateBuilder):
    def __init__(self, qubit_num: int, name='X_Ising') -> None:
        super().__init__(qubit_num, name)
        param_lambda = lambda params: params[0]
        if qubit_num == 1:
            self.append(Rx, [qubit_num - 1], param_lambda)
        else:
            # construct the multirxx
            for idx in range(qubit_num):
                self.append(H, [idx])
            for idx in range(qubit_num - 1):
                self.append(CX, [idx, idx + 1])
            self.append(Rz, [qubit_num - 1], param_lambda)
            for idx in range(qubit_num - 1, 0, -1):
                self.append(CX, [idx - 1, idx])
            for idx in range(qubit_num):
                self.append(H, [idx])


class Y_IsingGateBuilder(GateBuilder):
    def __init__(self, qubit_num: int, name='Y_Ising') -> None:
        super().__init__(qubit_num, name)
        param_lambda = lambda params: params[0]
        if qubit_num == 1:
            self.append(Ry, [qubit_num - 1], param_lambda)
        else:
            # construct the multirxx
            for idx in range(qubit_num):
                self.append(Rx, [idx], pi / 2)
            for idx in range(qubit_num - 1):
                self.append(CX, [idx, idx + 1])
            self.append(Rz, [qubit_num-1], param_lambda)
            for idx in range(qubit_num - 1, 0, -1):
                self.append(CX, [idx - 1, idx])
            for idx in range(qubit_num):
                self.append(Rx, [idx], -pi / 2)
