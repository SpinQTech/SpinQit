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
from .gates import *

def control_basis_decomposition(gate: Gate, qubits: List) -> List:
    if gate == X:
       return [(CX, [qubits[0], qubits[1]])]
    elif gate == Y:
        return [(CY, [qubits[0], qubits[1]])]
    elif gate == Z:
        return [(CZ, [qubits[0], qubits[1]])] 
    elif gate == I:
        return [(I, [qubits[0]]), (I, [qubits[1]])]
    elif gate == H:
        return CH_decomposition(qubits)
    elif gate == P:
        return CP_decomposition(qubits)
    elif gate == T:
        return CT_decomposition(qubits)
    elif gate == Td:
        return CTd_decomposition(qubits)
    elif gate == S:
        return CS_decomposition(qubits)
    elif gate == Sd:
        return CSd_decomposition(qubits)
    elif gate == U:
        return CU_decomposition(qubits)
    elif gate == Rx:
        return CRx_decomposition(qubits)
    elif gate == Ry:
        return CRy_decomposition(qubits)
    elif gate == Rz:
        return CRz_decomposition(qubits)
    elif gate == CX or gate.label == 'CX':
        return CCX_decomposition(qubits)
    elif gate == CZ:
        return CCZ_decomposition(qubits)
   
    return []

def CH_decomposition(qubits: List):
    __factors = []
    __factors.append((H, [qubits[1]]))
    __factors.append((Sd, [qubits[1]]))
    __factors.append((CX, [qubits[0],qubits[1]]))
    __factors.append((H, [qubits[1]]))
    __factors.append((T, [qubits[1]]))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((T, [qubits[1]]))
    __factors.append((H, [qubits[1]]))
    __factors.append((S, [qubits[1]]))
    __factors.append((X, [qubits[1]]))
    __factors.append((S, [qubits[0]]))
    return __factors

def CP_decomposition(qubits: List):
    __factors = []
    __factors.append((P, [qubits[0]], lambda params: params[0]/2))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((P, [qubits[1]], lambda params: -params[0]/2))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((P, [qubits[1]], lambda params: params[0]/2))
    return __factors

def CT_decomposition(qubits: List):
    __factors = []
    __factors.append((P, [qubits[0]], lambda *args: pi/8))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((P, [qubits[1]], lambda *args: -pi/8))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((P, [qubits[1]], lambda *args: pi/8))
    return __factors

def CTd_decomposition(qubits: List):
    __factors = []
    __factors.append((P, [qubits[0]], lambda *args: -pi/8))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((P, [qubits[1]], lambda *args: pi/8))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((P, [qubits[1]], lambda *args: -pi/8))
    return __factors

def CS_decomposition(qubits: List):
    __factors = []
    __factors.append((T, [qubits[0]]))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((Td, [qubits[1]]))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((T, [qubits[1]]))
    return __factors

def CSd_decomposition(qubits: List):
    __factors = []
    __factors.append((Td, [qubits[0]]))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((T, [qubits[1]]))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((Td, [qubits[1]]))
    return __factors

def CU_decomposition(qubits: List):
    __factors = []
    __factors.append((P, [qubits[0]], lambda params: (params[2]+params[1])/2))
    __factors.append((P, [qubits[1]], lambda params: (params[2]-params[1])/2))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((U, [qubits[1]], lambda params: (-params[0]/2, 0, -(params[2]+params[1]))))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((U, [qubits[1]], lambda params: (params[0]/2, params[1], 0)))
    return __factors

def CRx_decomposition(qubits: List):
    __factors = []
    __factors.append((Rz, [qubits[1]], lambda *args: pi/2))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((Ry, [qubits[1]], lambda params: -params[0]/2))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((Ry, [qubits[1]], lambda params: params[0]/2))
    __factors.append((Rz, [qubits[1]], lambda *args: -pi/2))
    return __factors

def CRy_decomposition(qubits: List):
    __factors = []
    __factors.append((Ry, [qubits[1]], lambda params: params[0]/2))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((Ry, [qubits[1]], lambda params: -params[0]/2))
    __factors.append((CX, [qubits[0], qubits[1]]))
    return __factors

def CRz_decomposition(qubits: List):
    __factors = []
    __factors.append((Rz, [qubits[1]], lambda params: params[0]/2))
    __factors.append((CX, [qubits[0], qubits[1]]))
    __factors.append((Rz, [qubits[1]], lambda params: -params[0]/2))
    __factors.append((CX, [qubits[0], qubits[1]]))
    return __factors


def CCX_decomposition(qubits: List):
    __factors = []
    __factors.append((H, [qubits[2]]))
    __factors.append((CX, [qubits[1],qubits[2]]))
    __factors.append((Td, [qubits[2]]))
    __factors.append((CX, [qubits[0],qubits[2]]))
    __factors.append((T, [qubits[2]]))
    __factors.append((CX, [qubits[1],qubits[2]]))
    __factors.append((Td, [qubits[2]]))
    __factors.append((CX, [qubits[0],qubits[2]]))
    __factors.append((T, [qubits[1]]))
    __factors.append((T, [qubits[2]]))
    __factors.append((H, [qubits[2]]))
    __factors.append((CX, [qubits[0],qubits[1]]))
    __factors.append((T, [qubits[0]]))
    __factors.append((Td, [qubits[1]]))
    __factors.append((CX, [qubits[0],qubits[1]]))
    return __factors

def CCZ_decomposition(qubits: List):
    __factors = []
    __factors.append((H, [qubits[2]]))
    __factors.extend(CCX_decomposition(qubits))
    __factors.append((H, [qubits[2]]))
    return __factors