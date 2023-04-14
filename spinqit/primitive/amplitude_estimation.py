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
from typing import List, Any
from spinqit.model import Gate, Instruction, GateBuilder, RepeatBuilder
from spinqit.primitive import PhaseEstimation
from spinqit import H, X, Z, Ry, P, MultiControlPhaseGateBuilder, InverseBuilder
import math

class AmplitudeEstimation(object):
    def __init__(self, counting_num: int, searching_num: int, prep: Gate, oracle: Gate, prep_params: List = [], oracle_params: List = []):
        self.__prep = prep
        self.__prep_params = prep_params
        self.__oracle = oracle
        self.__oracle_params = oracle_params
        self.__counting_num = counting_num
        self.__searching_num = searching_num

    def _Qoperator(self) -> Gate:
        Q_builder = GateBuilder(self.__searching_num)
        
        ora_lambda = lambda *args: self.__oracle_params[0]
        oracle_inv = InverseBuilder(self.__oracle).to_gate()

        Q_builder.append(Z, list(range(self.__searching_num)))
        Q_builder.append(oracle_inv, list(range(self.__searching_num)), ora_lambda)
        
        xBuilder = RepeatBuilder(X, self.__searching_num)
        mcz_builder = MultiControlPhaseGateBuilder(self.__searching_num-1)
        Q_builder.append(xBuilder.to_gate(), list(range(self.__searching_num)))
        Q_builder.append(mcz_builder.to_gate(), list(range(self.__searching_num)), math.pi)
        Q_builder.append(xBuilder.to_gate(), list(range(self.__searching_num)))
        Q_builder.append(self.__oracle, list(range(self.__searching_num)), ora_lambda)

        # global phase fix
        Q_builder.append(X, [0])
        Q_builder.append(Z, [0])
        Q_builder.append(X, [0])
        Q_builder.append(Z, [0])

        return Q_builder.to_gate()

    def build(self):
        inst_list = []
        count_qubits = list(range(self.__counting_num))
        oracle_qubits = [i+self.__counting_num for i in range(self.__searching_num)]
        inst_list.append(Instruction(self.__prep, oracle_qubits, [], self.__prep_params))

        Q_gate = self._Qoperator()
        qpe = PhaseEstimation(Q_gate, oracle_qubits, count_qubits)
        inst_list.extend(qpe.build())

        return inst_list
