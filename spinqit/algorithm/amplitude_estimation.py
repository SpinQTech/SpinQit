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
from typing import Union, List
from spinqit import Gate, Circuit, get_compiler
from spinqit import check_backend_and_config
from spinqit.primitive import QOperatorBuilder, PhaseEstimation
import numpy as np

class AmplitudeEstimation():
    def __init__(self, eval_num: int, A: Gate, params: Union[float,List] = None, backend_mode: str = 'spinq', **kwargs):
        self.A = A
        self.params = params
        self.eval_num = eval_num
        self.backend_mode = backend_mode
        self.backend, self.config = check_backend_and_config(backend_mode, **kwargs)
        
    def run(self) -> float:
        circ = self._build_circuit()
        comp = get_compiler()
        exe = comp.compile(circ, 0)
        self.config.configure_measure_qubits(list(range(self.eval_num)))
        result = self.backend.execute(exe, self.config)
        samples = {}
        M = 2**(self.eval_num-1)
        for bval, prob in result.probabilities.items():
            y = int(bval, 2)
            if y > M:
                y = 2*M - y
            key = np.round(np.power(np.sin(y * np.pi / 2 ** self.eval_num), 2), decimals=7)
            if key in samples:
                samples[key] += prob
            else:
                samples[key] = prob

        estimation = 0.0
        for key, val in samples.items():
            estimation += key * val
        return 1.0 - estimation

    def _build_circuit(self) -> Circuit:
        circ = Circuit()
        eval_reg = circ.allocateQubits(self.eval_num)
        op_reg = circ.allocateQubits(self.A.qubit_num)
        if self.params is None:
            circ << (self.A, op_reg)
            Q = QOperatorBuilder(self.A).to_gate()
        else:
            circ << (self.A, op_reg, self.params)
            Q = QOperatorBuilder(self.A, self.params).to_gate()
        qpe_insts = PhaseEstimation(Q, op_reg, eval_reg).build()
        circ.extend(qpe_insts)
        return circ
        
# def _Qoperator(self) -> Gate:
    #     Q_builder = GateBuilder(self.__searching_num)
        
    #     ora_lambda = lambda *args: self.__oracle_params
    #     oracle_inv = InverseBuilder(self.__oracle).to_gate()

    #     Q_builder.append(Z, [self.__searching_num-1])
    #     # Q_builder.append(Z, [0])
    #     Q_builder.append(oracle_inv, list(range(self.__searching_num)), ora_lambda)
        
    #     xBuilder = RepeatBuilder(X, self.__searching_num)
    #     mcz_builder = MultiControlPhaseGateBuilder(self.__searching_num-1)
    #     Q_builder.append(xBuilder.to_gate(), list(range(self.__searching_num)))
    #     Q_builder.append(mcz_builder.to_gate(), list(range(self.__searching_num)), math.pi)
    #     Q_builder.append(xBuilder.to_gate(), list(range(self.__searching_num)))
    #     Q_builder.append(self.__oracle, list(range(self.__searching_num)), ora_lambda)

    #     # global phase fix
    #     Q_builder.append(X, [0])
    #     Q_builder.append(Z, [0])
    #     Q_builder.append(X, [0])
    #     Q_builder.append(Z, [0])

    #     return Q_builder.to_gate()
        
