# Copyright 2023 SpinQ Technology Co., Ltd.
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
from spinqit.backend import check_backend_and_config
from spinqit import Gate, GateBuilder, Circuit, get_compiler
from spinqit import H, X, Z, RepeatBuilder, MultiControlledGateBuilder

def get_grover_coin(coin_qubit_num: int) -> Gate:
    builder = GateBuilder(coin_qubit_num)
    hbuilder = RepeatBuilder(H, coin_qubit_num)
    xbuilder = RepeatBuilder(X, coin_qubit_num)
    mcz_builder = MultiControlledGateBuilder(coin_qubit_num-1, Z)
    builder.append(hbuilder.to_gate(), list(range(coin_qubit_num)))
    builder.append(xbuilder.to_gate(), list(range(coin_qubit_num)))
    builder.append(mcz_builder.to_gate(), list(range(coin_qubit_num)))
    builder.append(xbuilder.to_gate(), list(range(coin_qubit_num)))
    builder.append(hbuilder.to_gate(), list(range(coin_qubit_num)))
    return builder.to_gate()

class CoinedQuantumWalk:
    def __init__(self, state_qubit_num: int, coin_qubit_num: int, init_operator: Gate, 
                coin_operator: Gate, shift_operator: Gate, backend_mode: str, **kwargs):
        self.__state_qubit_num = state_qubit_num
        self.__coin_qubit_num = coin_qubit_num
        self.__init_operator = init_operator
        self.__coin_operator = coin_operator
        self.__shift_operator = shift_operator
        self.__backend, self.__config = check_backend_and_config(backend_mode, **kwargs)
        self.__config.configure_measure_qubits(list(range(state_qubit_num)))

    def _build_circuit(self, steps: int) -> Circuit:
        circuit = Circuit()
        state_qubits = circuit.allocateQubits(self.__state_qubit_num)
        coin_qubits = circuit.allocateQubits(self.__coin_qubit_num)
        circuit << (self.__init_operator, state_qubits+coin_qubits)
        for step in range(steps):
            circuit << (self.__coin_operator, coin_qubits)
            circuit << (self.__shift_operator, state_qubits+coin_qubits)
        return circuit

    def walk(self, steps: int):
        circuit = self._build_circuit(steps)
        compiler = get_compiler()
        exe = compiler.compile(circuit, 0)
        result = self.__backend.execute(exe, self.__config)
        return result.probabilities
         