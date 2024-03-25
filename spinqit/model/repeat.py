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
from typing import Union, Callable, List
from spinqit.model import Gate, GateBuilder

class RepeatBuilder(GateBuilder):
    def __init__(self, g: Gate, repeat: int, param_lambda: Union[float,Callable,List] = None):
        super().__init__(g.qubit_num * repeat)
        if isinstance(param_lambda, float):
            param_lambda = lambda *args: param_lambda
        for i in range(repeat):
            if param_lambda is None:
                self.append(g, list(range(i * g.qubit_num, (i+1) * g.qubit_num)))
            else:
                self.append(g, list(range(i * g.qubit_num, (i+1) * g.qubit_num)), param_lambda)
