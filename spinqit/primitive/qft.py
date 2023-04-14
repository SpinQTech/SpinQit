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
from math import pi
from spinqit.model import Gate, GateBuilder, InverseBuilder
from spinqit.model import H, CP, SWAP

class QFT(object):
    def __init__(self, 
                qubit_num: int):
        self.__qubit_num = qubit_num
        if self.__qubit_num <= 0:
            raise ValueError
        self.__builder = GateBuilder(self.__qubit_num)

        for i in range(self.__qubit_num):
            self.__builder.append(H, [i])
            for j in range(i+1, self.__qubit_num):
                shift = pi / (2 ** (j - i))
                self.__builder.append(CP, [j, i], shift)
        
        for i in range(self.__qubit_num // 2):
            self.__builder.append(SWAP, [i, self.__qubit_num - i -1])
    
    def build(self) -> Gate:
        return self.__builder.to_gate()

    def inverse(self) -> Gate:
        iBuilder = InverseBuilder(self.__builder.to_gate())
        inv = iBuilder.to_gate()
        return inv

    