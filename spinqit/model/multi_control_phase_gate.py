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
# from .basic_gate import GateBuilder
from .matrix_gate import MultiControlledMatrixGateBuilder
from .gates import P, CP, CX

def _generate_gray_code(bit_num: int):
    result = []
    for i in range(2 ** bit_num):
        bit_str = format((i ^ (i >> 1)), "0%sb" % bit_num)
        result.append(bit_str)
    return result

class MultiControlPhaseGateBuilder(MultiControlledMatrixGateBuilder):
    def __init__(self, ctrl_qubit_num: int) -> None:
        if ctrl_qubit_num < 0:
            raise ValueError
        # super().__init__(ctrl_qubit_num + 1)
        super().__init__(P.matrix, ctrl_qubit_num, ctrl_qubit_num+1)
        if ctrl_qubit_num == 0:
            self._GateBuilder__gate = P
        elif ctrl_qubit_num == 1:
            self._GateBuilder__gate = CP
        else:
            param_lambda = lambda params: params[0] / (2 ** (ctrl_qubit_num - 1))
            inverse_lambda = lambda params: -1 * params[0] / (2 ** (ctrl_qubit_num - 1))
            
            patterns = _generate_gray_code(ctrl_qubit_num)
            last_pattern = None
            for pattern in patterns:
                if '1' not in pattern:
                    continue
                if last_pattern is None:
                    last_pattern = pattern
                left_most = list(pattern).index('1')
                pos = 0
                for i, j in zip(pattern, last_pattern):
                    if i != j:
                        break
                    else:
                        pos += 1
                if pos < ctrl_qubit_num:
                    if pos != left_most:
                        self.append(CX, [pos, left_most])
                    else:
                        indices = [i for i, x in enumerate(pattern) if x == "1"]
                        for idx in indices[1:]:
                            self.append(CX, [idx, left_most])
                if pattern.count('1') % 2 == 0:
                    self.append(CP, [left_most, ctrl_qubit_num], inverse_lambda)
                else:
                    self.append(CP, [left_most, ctrl_qubit_num], param_lambda)
                last_pattern = pattern
            
        
