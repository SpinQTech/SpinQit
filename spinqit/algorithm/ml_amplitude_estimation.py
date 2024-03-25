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
from typing import List, Tuple, Union
from spinqit import Gate, Circuit, get_compiler
from spinqit import check_backend_and_config
from spinqit.primitive import QOperatorBuilder, generate_power_gate
import numpy as np
from scipy.stats import norm
from scipy.optimize import shgo
from math import pi

class MaximumLikelihoodAmplitudeEstimation():
    def __init__(self, circuit_num: int, A: Gate, params: Union[float,List] = None, alpha: float = 0.05, backend_mode: str = 'spinq', **kwargs):
        self.circuit_num = circuit_num
        self.alpha = alpha
        self.exponents = [0] + [2**j for j in range(circuit_num)]
        self.A = A
        self.params = params
        self.backend, self.config = check_backend_and_config(backend_mode, **kwargs)

    def run(self) -> Tuple:
        circuits = self.build_circuits()
        values = []
        compiler = get_compiler()
        self.config.configure_measure_qubits([self.A.qubit_num-1])
        for circ in circuits:
            exe = compiler.compile(circ, 0)
            result = self.backend.execute(exe, self.config)
            one_prob = result.probabilities['1']
            values.append(one_prob)
        
        def loglikelihood(theta):
            loglik = 0
            for i, k in enumerate(self.exponents):
                loglik += np.log(np.sin((2 * k + 1) * theta) ** 2) * values[i]
                loglik += np.log(np.cos((2 * k + 1) * theta) ** 2) * (1.0 - values[i])
            return -loglik
        est_theta = shgo(loglikelihood, [(0, pi/2)])
        estimation = np.sin(est_theta.x[0])**2
        confidence_interval = self.calculate_interval(estimation)
        return estimation, confidence_interval

    def build_circuits(self) -> List:
        if self.params is None:
            Q = QOperatorBuilder(self.A).to_gate()
        else:
            Q = QOperatorBuilder(self.A, self.params).to_gate()
        circuits = []
        for k in self.exponents:
            circ = Circuit()
            qreg = circ.allocateQubits(self.A.qubit_num)
            if self.params is None:
                circ << (self.A, qreg)    
            else:
                circ << (self.A, qreg, self.params)
            inst_list = generate_power_gate(Q, k, qreg)
            circ.extend(inst_list)
            circuits.append(circ)
        return circuits

    def calculate_interval(self, estimation: float) -> List:
        fisher_info = sum(1.0 * (2 * m_k + 1)**2 for m_k in self.exponents)
        fisher_info /= estimation * (1 - estimation)
        normal_quantile = norm.ppf(1 - self.alpha / 2)
        return [estimation + normal_quantile / np.sqrt(fisher_info) * i for i in [-1, 1]]
