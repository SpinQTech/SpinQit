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
from spinqit import get_compiler, BasicSimulatorBackend, BasicSimulatorConfig
from spinqit.model import Gate, GateBuilder, Circuit, RepeatBuilder, ControlledGate, InverseBuilder
from spinqit.model import H, X, P, CX, SWAP
from spinqit.primitive import QFT

from typing import List, Any
import numpy as np
from fractions import Fraction
from math import gcd

class Shor(object):
    repeat_limit = 1024
    def __init__(self, N: int, backend: Any):
        self.N = N
        self.compiler = get_compiler('native')
        self.backend = backend
        if not isinstance(self.backend, BasicSimulatorBackend):
            raise ValueError('Only the basic simulator can be used to run the Shor algorithm.')
        # self.a = random.randint(2, self.N-1)
        # while gcd(self.a, self.N) != 1 and self.a in self.tried:
        #     self.a = random.randint(2, self.N-1)
        
    def get_quantum_result(self):
        circ = self._build()
        exe = self.compiler.compile(circ, 0)
        if isinstance(self.backend, BasicSimulatorBackend): 
            config = BasicSimulatorConfig()
            config.configure_measure_qubits(list(range(self.N.bit_length()*2)))
            result = self.backend.execute(exe, config)
            return result
        return None
    
    def get_factor(self, a: int) -> List:
        if not isinstance(a, int) or a < 2 or a > self.N or gcd(a, self.N) != 1:
            raise ValueError('The a value is invalid.')
        self.a = a
        result = self.get_quantum_result()
        attempt = 0
        factor_found = False
        factors = []
        while not factor_found and attempt < Shor.repeat_limit:
            attempt = attempt + 1
            reading = result.get_random_reading()
            phase = int(reading, 2) / (2**(self.N.bit_length()*2))
            if phase != 0:
                frac = Fraction(phase).limit_denominator(self.N)
                r = frac.denominator
                if r % 2 == 0:
                    guesses = [gcd(a**(r//2)-1, self.N), gcd(a**(r//2)+1, self.N)]
                    for guess in guesses:
                        if guess not in [1, self.N] and (self.N % guess) == 0:
                            factors.append(guess)
                            factor_found = True
        return factors

    def _build(self) -> Circuit:
        nbit = self.N.bit_length()
        circ = Circuit()
        reg_ctrl = circ.allocateQubits(nbit*2)
        reg_x = circ.allocateQubits(nbit)
        reg_ancilla = circ.allocateQubits(nbit+2)

        h_builder = RepeatBuilder(H, nbit*2)
        circ << (h_builder.to_gate(), reg_ctrl)
        circ << (X, reg_x[0])

        power_mod_N = self._CU_power()
        circ << (power_mod_N, reg_ctrl+reg_x+reg_ancilla)

        iqft = QFT(nbit*2)
        circ << (iqft.inverse(), reg_ctrl)
        return circ

    def _calc_angles(self, a: int, n: int) -> List:
        bits = bin(int(a))[2:].zfill(n)
        coeffs = [0.0] * n
        for i in range(n):
            for j in range(i+1):
                if bits[j] == '1':
                    coeffs[i] += pow(2, (j-i))
        return [coeff * np.pi for coeff in coeffs]

    def _phi_adder(self, angles: List) -> Gate:
        qnum = len(angles)
        builder = GateBuilder(qnum)
        for i in range(qnum):
            plam = lambda params, idx=i: angles[idx]
            builder.append(P, [i], plam)
        return builder.to_gate()

    def _CU_power(self) -> Gate:
        nbit = self.N.bit_length()
        builder = GateBuilder(4*nbit+2)

        qft = QFT(nbit+1)
        N_angles = self._calc_angles(self.N, nbit+1)
        phi_add_N = self._phi_adder(N_angles)

        for i in range( nbit * 2 ):
            part = pow(self.a, pow(2, i), self.N)
            cmult_mod = self._CMULT_mod_N(part, phi_add_N, qft)
            builder.append(cmult_mod, [i]+list(range(2*nbit, 4*nbit+2)))
        return builder.to_gate()

    def _CMULT_mod_N(self, part: int, adder: Gate, qft: QFT) -> Gate:
        nbit = self.N.bit_length()
        builder = GateBuilder(2*nbit+3)

        qft_gate = qft.build()
        builder.append(qft_gate, list(range(nbit+1, 2*nbit+2)))
        
        c_adder = ControlledGate(adder)
        i_adder = InverseBuilder(adder).to_gate()

        for i in range(nbit):
            pa = (pow(2, i, self.N) * part) % self.N
            angles = self._calc_angles(pa, nbit+1)
            adder_mod_N = self._generate_two_ctrl_add_mod_N(c_adder, i_adder, qft, angles)
            builder.append(adder_mod_N, [0]+[i+1]+list(range(nbit+1, 2*nbit+3)))

        iqft_gate = qft.inverse()
        builder.append(iqft_gate, list(range(nbit+1, 2*nbit+2)))
        
        cswap = ControlledGate(SWAP)
        for i in range(nbit):
            builder.append(cswap, [0, i+1, nbit+i+1])

        builder.append(qft_gate, list(range(nbit+1, 2*nbit+2)))

        part_inv = pow(part, -1, mod=self.N)
        for i in reversed(range(nbit)):
            pa_inv = (pow(2, i, self.N) * part_inv) % self.N
            angles = self._calc_angles(pa_inv, nbit+1)
            adder_mod_N = self._generate_two_ctrl_add_mod_N(c_adder, i_adder, qft, angles)
            adder_mod_N_inv = InverseBuilder(adder_mod_N).to_gate()
            builder.append(adder_mod_N_inv, [0]+[i+1]+list(range(nbit+1, 2*nbit+3)))
        builder.append(iqft_gate, list(range(nbit+1, 2*nbit+2)))
        return builder.to_gate()

    def _generate_two_ctrl_add_mod_N(self, c_phi_add_N: Gate, i_phi_add_N: Gate, qft: QFT, angles: List):
        plen = len(angles)
        builder = GateBuilder(3+plen)
        phi_add_p = self._phi_adder(angles)
        c_phi_add_p = ControlledGate(phi_add_p)
        c2_phi_add_p = ControlledGate(c_phi_add_p)
        ic2_phi_add_p = InverseBuilder(c2_phi_add_p).to_gate()
        builder.append(c2_phi_add_p, list(range(plen+2)))

        qft_gate = qft.build()
        iqft_gate = qft.inverse()
        builder.append(i_phi_add_N, list(range(2, plen+2)))
        builder.append(iqft_gate, list(range(2, plen+2)))
        builder.append(CX, [plen+1, plen+2])
        builder.append(qft_gate, list(range(2, plen+2)))

        builder.append(c_phi_add_N, [plen+2] + list(range(2, plen+2)))
        builder.append(ic2_phi_add_p, list(range(plen+2)))

        builder.append(iqft_gate, list(range(2, plen+2)))
        builder.append(X, [plen+1])
        builder.append(CX, [plen+1, plen+2])
        builder.append(X, [plen+1])
        builder.append(qft_gate, list(range(2, plen+2)))
        builder.append(c2_phi_add_p, list(range(plen+2)))
        return builder.to_gate()