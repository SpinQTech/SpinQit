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

from .exceptions import *
from .circuit import Circuit
from .parameter import Parameter, PlaceHolder
from .register import QuantumRegister
from .instruction import Instruction
from .basic_gate import Gate, GateBuilder
from .matrix_gate import MatrixGate, MatrixGateBuilder, MultiControlledMatrixGate, MultiControlledMatrixGateBuilder
from .inverse_builder import *
from .controlled_gate import ControlledGate
from .repeat import RepeatBuilder
from .multi_control_phase_gate import MultiControlPhaseGateBuilder
from .gates import I, H, X, Y, Z, Rx, Ry, Rz, P, T, Td, S, Sd, CX, CNOT, CY, CZ, CP, SWAP, CCX, U, Ph, CSWAP, MEASURE, BARRIER, StateVector