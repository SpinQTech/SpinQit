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
from spinqit import get_compiler
from spinqit.model import Gate, Circuit, GateBuilder, RepeatBuilder
from spinqit.primitive import PhaseEstimation
from spinqit import H, X, MultiControlPhaseGateBuilder
import math

class QuantumCounting(object):
    def __init__(self, counting_num: int, searching_num: int, prep: Gate, oracle: Gate, prep_params: List = [], oracle_params: List = []):
        self.__prep = prep
        self.__prep_params = prep_params
        self.__oracle = oracle
        self.__oracle_params = oracle_params
        self.__counting_num = counting_num
        self.__searching_num = searching_num
        self.__circuit = self._build()

    def _grover(self) -> Gate:
        grover_builder = GateBuilder(self.__searching_num)
        ora_lambda = lambda *args: self.__oracle_params
        grover_builder.append(self.__oracle, list(range(self.__searching_num)), ora_lambda)
        hBuilder = RepeatBuilder(H, self.__searching_num)
        xBuilder = RepeatBuilder(X, self.__searching_num)
        mcz_builder = MultiControlPhaseGateBuilder(self.__searching_num - 1)
        grover_builder.append(hBuilder.to_gate(), list(range(self.__searching_num)))
        grover_builder.append(xBuilder.to_gate(), list(range(self.__searching_num)))
        grover_builder.append(mcz_builder.to_gate(), list(range(self.__searching_num)), math.pi)
        grover_builder.append(xBuilder.to_gate(), list(range(self.__searching_num)))
        grover_builder.append(hBuilder.to_gate(), list(range(self.__searching_num)))
        return grover_builder.to_gate()

    def _build(self) -> Circuit:
        circ = Circuit()
        count_qubits = circ.allocateQubits(self.__counting_num)
        oracle_qubits = circ.allocateQubits(self.__searching_num)

        circ << (self.__prep, oracle_qubits, self.__prep_params)
        grover_gate = self._grover()
        qpe = PhaseEstimation(grover_gate, oracle_qubits, count_qubits)
        circ.extend(qpe.build())

        return circ

    def get_circuit(self):
        return self.__circuit

    def run(self, backend: Any, config: Any):
        compiler = get_compiler("native")
        optimization_level = 0
        exe = compiler.compile(self.__circuit, optimization_level)
        
        config.configure_measure_qubits(list(range(self.__counting_num)))
        result = backend.execute(exe, config)
        measured_str = max(result.probabilities, key=result.probabilities.get)
        
        reading = int(measured_str, 2)
        theta = (reading/(2**self.__counting_num)) * math.pi * 2
        N = 2 ** self.__searching_num
        M = N * (math.sin(theta/2)**2)
        return N - M
