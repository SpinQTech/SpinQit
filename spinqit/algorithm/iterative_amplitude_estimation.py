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
from spinqit import sv_backends, check_backend_and_config
from spinqit.primitive import QOperatorBuilder, generate_power_gate
import numpy as np
from scipy.stats import beta
from math import pi

class IterativeAmplitudeEstimation():
    def __init__(self, A: Gate, params: Union[float,List] = None, target_accuracy: float = 1e-6, alpha: float = 0.05, shots: int = 1000, cf_method: str = 'clopper-pearson', backend_mode: str = 'spinq', **kwargs):
        self.epsilon = target_accuracy
        self.alpha = alpha
        self.shots = shots
        self.A = A
        self.params = params
        self.T = int(np.log(2.0 * np.pi / 8
                                / self.epsilon) / np.log(2.0)) + 1
        self.cf_method = cf_method
        self.backend_mode = backend_mode
        self.backend, self.config = check_backend_and_config(backend_mode, **kwargs)

    def run(self) -> Tuple:
        estimation = 0.0
        confidence_interval = []
        ki = 0
        upper = True
        theta_l = 0.0
        theta_u = 0.25
        
        compiler = get_compiler()
        self.config.configure_shots(self.shots)
        self.config.configure_measure_qubits([self.A.qubit_num-1])

        if self.backend_mode not in sv_backends:
            circ = self._build_circuit(0)
            exe = compiler.compile(circ, 0)
            result = self.backend.execute(exe, self.config)
            estimation = result.probabilities['1']
            confidence_interval = [estimation, estimation]
        else:
            total_shots = 0
            total_positive = 0
            
            while theta_u - theta_l > 2 * self.epsilon:
                pre_k = ki
                ki, upper = self._get_next_k(pre_k, theta_l, theta_u, upper)
                Ki = 4 * ki + 2
                circ = self._build_circuit(ki)
                exe = compiler.compile(circ, 0)
                result = self.backend.execute(exe, self.config)
                ai = result.probabilities['1']
                positive = result.counts['1']
                if ki == pre_k:
                    total_shots += self.shots
                    total_positive += positive
                    ai = total_positive / total_shots
                else:
                    total_shots = self.shots
                    total_positive = positive
                if self.cf_method == 'clopper-pearson':
                    amin, amax = self._clopper_pearson(total_positive, total_shots)
                else:
                    amin, amax = self._chernoff_hoeffding(ai, total_shots)

                if upper:
                    theta_min = np.arccos(1-2*amin)/2/pi
                    theta_max = np.arccos(1-2*amax)/2/pi
                else:
                    theta_min = 1-np.arccos(1-2*amin)/2/pi
                    theta_max = 1-np.arccos(1-2*amax)/2/pi
                
                theta_l = (int(Ki*theta_l)+theta_min) / Ki
                theta_u = (int(Ki*theta_u)+theta_max) / Ki
                    
                confidence_interval = [np.sin(2*pi*theta_l)**2, np.sin(2*pi*theta_u)**2]
                estimation = np.mean(confidence_interval)
        
        return estimation, confidence_interval

    def _build_circuit(self, k: int) -> Circuit:
        circ = Circuit()
        qreg = circ.allocateQubits(self.A.qubit_num)
        if self.params is None:
            circ << (self.A, qreg)
            Q = QOperatorBuilder(self.A).to_gate()
        else:
            circ << (self.A, qreg, self.params)
            Q = QOperatorBuilder(self.A, self.params).to_gate()
        inst_list = generate_power_gate(Q, k, qreg)
        circ.extend(inst_list)
        return circ

    def _chernoff_hoeffding(self, value: float, N: int) -> Tuple:
        eps_a = np.sqrt(3 * np.log(2*self.T/self.alpha)/N)
        amax = np.minimum(1, value + eps_a)
        amin = np.maximum(0, value - eps_a)
        return amin, amax
        
    def _clopper_pearson(self, positive: int, N: int) -> Tuple:
        amin, amax = 0, 1
        if positive != 0:
            amin = beta.ppf(self.alpha / 2, positive, N - positive + 1)
        if positive != N:
            amax = beta.ppf(1 - self.alpha / 2, positive + 1, N - positive)
        return amin, amax

    def _get_next_k(self, ki: int, theta_l: float, theta_u: float, upper: bool, r: float = 2.0):
        Ki = 4 * ki + 2
        # theta_min = Ki * theta_l
        # theta_max = Ki * theta_u
        K_max = int(1 /(2*(theta_u - theta_l)))
        K = K_max - (K_max-2) % 4
        while K >= r*Ki:
            # q = K / Ki
            # radian_max = (q*theta_max)%(2*pi)
            # radian_min = (q*theta_min)%(2*pi)
            theta_min = K * theta_l - int(K * theta_l)
            theta_max = K * theta_u - int(K * theta_u)
            
            if theta_min <= theta_max <= 0.5 and theta_min <= 0.5:
                nextk = (K - 2) / 4
                return nextk, True
            elif theta_max >= 0.5 and theta_max >= theta_min >= 0.5:
                nextk = (K - 2) / 4
                return nextk, False
            K = K - 4
        return ki, upper

