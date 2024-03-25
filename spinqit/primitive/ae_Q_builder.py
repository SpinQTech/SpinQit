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
from typing import Union, Callable, List
from spinqit.model import Gate, GateBuilder, RepeatBuilder
from spinqit import X, Z, MultiControlPhaseGateBuilder, InverseBuilder
from math import pi

class QOperatorBuilder(GateBuilder):
    def __init__(self, A: Gate, param_lambda: Union[float,Callable,List] = None):
        super().__init__(A.qubit_num)
        if isinstance(param_lambda, float):
            local_lambda = lambda *args: param_lambda
        elif isinstance(param_lambda, list) and isinstance(param_lambda[0], float):
            local_lambda = lambda *args: param_lambda
        else:
            local_lambda = param_lambda

        A_inv = InverseBuilder(A).to_gate()
        self.append(Z, [A.qubit_num-1])
        if local_lambda is None:
            self.append(A_inv, list(range(A.qubit_num)))
        else:
            self.append(A_inv, list(range(A.qubit_num)), local_lambda)
        xBuilder = RepeatBuilder(X, A.qubit_num)
        mcz_builder = MultiControlPhaseGateBuilder(A.qubit_num-1)
        self.append(xBuilder.to_gate(), list(range(A.qubit_num)))
        self.append(mcz_builder.to_gate(), list(range(A.qubit_num)), pi)
        self.append(xBuilder.to_gate(), list(range(A.qubit_num)))
        if local_lambda is None:
            self.append(A, list(range(A.qubit_num)))
        else:
            self.append(A, list(range(A.qubit_num)), local_lambda)