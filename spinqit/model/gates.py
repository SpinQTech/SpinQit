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

import sys
import numpy as np
from cmath import exp, sqrt, sin, cos
from .basic_gate import Gate, GateBuilder

I = Gate('I', 1)
I.matrix = lambda *args: np.eye(2)

H = Gate('H', 1)
H.matrix = lambda *args: 1/sqrt(2) * np.array([[1,1],[1,-1]])

X = Gate('X', 1)
X.matrix = lambda *args: np.array([[0,1],[1,0]])

Y = Gate('Y', 1)
Y.matrix = lambda *args: np.array([[0,-1j],[1j,0]], dtype=np.complex64)

Z = Gate('Z', 1)
Z.matrix = lambda *args: np.array([[1,0],[0,-1]])

Rx = Gate('Rx', 1)
Rx.matrix = lambda params: np.array([[cos(params[0]/2), -1j * sin(params[0]/2)],
                                    [-1j * sin(params[0]/2), cos(params[0]/2)]])

Ry = Gate('Ry', 1)
Ry.matrix = lambda params: np.array([[cos(params[0]/2), -sin(params[0]/2)], 
                                     [sin(params[0]/2), cos(params[0]/2)]])

Rz = Gate('Rz', 1)
Rz.matrix = lambda params: np.array([[exp(-1j*params[0]/2), 0], [0, exp(1j*params[0]/2)]])

P = Gate('P', 1)
P.matrix = lambda params: np.array([[1, 0], [0, exp(1j*params[0])]])

T = Gate('T', 1)
T.matrix = lambda *args: np.array([[1,0], [0,(1+1j)/sqrt(2)]])

Td = Gate('Td', 1)
Td.matrix = lambda *args: np.array([[1,0], [0,(1-1j)/sqrt(2)]])

S = Gate('S', 1)
S.matrix = lambda *args: np.array([[1,0], [0, 1j]])

Sd = Gate('Sd', 1)
Sd.matrix = lambda *args: np.array([[1,0], [0, -1j]])

CX = Gate('CX', 2)
CX.matrix = lambda params: np.array([[1,0,0,0], [0,1,0,0], [0,0,0,1], [0,0,1,0]]) if params[0] == 0 else \
                           np.array([[1,0,0,0], [0,0,0,1], [0,0,1,0], [0,1,0,0]])

CNOT = CX

CY = Gate('CY', 2)
CY.matrix = lambda params: np.array([[1,0,0,0], [0,1,0,0], [0,0,0,-1j], [0,0,1j,0]]) if params[0] == 0 else \
                           np.array([[1,0,0,0], [0,0,0,-1j], [0,0,1,0], [0,1j,0,0]])

CZ = Gate('CZ', 2)
CZ.matrix = lambda *args: np.array([[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,-1]])

U_builder = GateBuilder(1)
U_builder.append(Rz, [0], lambda params: params[2])
U_builder.append(Ry, [0], lambda params: params[0])
U_builder.append(Rz, [0], lambda params: -params[2])
U_builder.append(P, [0], lambda params: params[1]+params[2])
U = U_builder.to_gate()
U.label = 'U'
U.matrix = lambda params: np.array([[cos(params[0]/2), -exp(1j*params[2]) * sin(params[0]/2)], 
                                   [exp(1j*params[1]) * sin(params[0]/2), exp(1j*(params[1]+params[2])) * cos(params[0]/2)]])

SWAP_builder = GateBuilder(2, 'SWAP')
SWAP_builder.append(CX, [0, 1])
SWAP_builder.append(CX, [1, 0])
SWAP_builder.append(CX, [0, 1])

SWAP = SWAP_builder.to_gate()
SWAP.matrix = lambda *args: np.array([[1,0,0,0], [0,0,1,0], [0,1,0,0], [0,0,0,1]])

CCX_builder = GateBuilder(3, 'CCX')
CCX_builder.append(H, [2])
CCX_builder.append(CX, [1,2])
CCX_builder.append(Td, [2])
CCX_builder.append(CX, [0,2])
CCX_builder.append(T, [2])
CCX_builder.append(CX, [1,2])
CCX_builder.append(Td, [2])
CCX_builder.append(CX, [0,2])
CCX_builder.append(T, [1])
CCX_builder.append(T, [2])
CCX_builder.append(H, [2])
CCX_builder.append(CX, [0,1])
CCX_builder.append(T, [0])
CCX_builder.append(Td, [1])
CCX_builder.append(CX, [0,1])

CCX = CCX_builder.to_gate()
CCX.label = 'CCX'
CCX.matrix = lambda *args: np.array([[1,0,0,0,0,0,0,0], [0,1,0,0,0,0,0,0], [0,0,1,0,0,0,0,0], [0,0,0,1,0,0,0,0], [0,0,0,0,1,0,0,0], [0,0,0,0,0,1,0,0], [0,0,0,0,0,0,0,1], [0,0,0,0,0,0,1,0]])

# CP_builder = GateBuilder(2)
from .matrix_gate import MultiControlledMatrixGateBuilder
CP_builder = MultiControlledMatrixGateBuilder(P.matrix, 1, 2)
CP_builder.append(P, [0], lambda params: params[0]/2)
CP_builder.append(CX, [0, 1])
CP_builder.append(P, [1], lambda params: -params[0]/2)
CP_builder.append(CX, [0, 1])
CP_builder.append(P, [1], lambda params: params[0]/2)

CP = CP_builder.to_gate()

# Phase Gate
Ph_bulider = GateBuilder(1)

Ph_bulider.append(X, [0])
Ph_bulider.append(P, [0], lambda params: params[0])
Ph_bulider.append(X, [0])
Ph_bulider.append(P, [0], lambda params: params[0])

Ph = Ph_bulider.to_gate()


CSWAP_builder = GateBuilder(3, 'cswap')
CSWAP_builder.append(CX, [2, 1])
CSWAP_builder.append(CCX, [0, 1, 2])
CSWAP_builder.append(CX, [2, 1])
CSWAP = CSWAP_builder.to_gate()
CSWAP.matrix = lambda *args: np.array([[1, 0, 0, 0, 0, 0, 0, 0],
                                       [0, 1, 0, 0, 0, 0, 0, 0],
                                       [0, 0, 1, 0, 0, 0, 0, 0],
                                       [0, 0, 0, 1, 0, 0, 0, 0],
                                       [0, 0, 0, 0, 1, 0, 0, 0],
                                       [0, 0, 0, 0, 0, 0, 1, 0],
                                       [0, 0, 0, 0, 0, 1, 0, 0],
                                       [0, 0, 0, 0, 0, 0, 0, 1]])

MEASURE = Gate('MEASURE', sys.maxsize)
BARRIER = Gate('BARRIER', sys.maxsize)
StateVector = Gate('StateVector', sys.maxsize)
# AmplitudeStateEncoding = Gate('StateEncodingAmplitude', sys.maxsize)
