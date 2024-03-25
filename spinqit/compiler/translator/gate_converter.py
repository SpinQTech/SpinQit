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

import functools
from typing import List

from spinqit.utils.function import to_list

from spinqit.model import *
from ..decomposer.ZYZdecomposer import decompose_zyz
from ..ir import IntermediateRepresentation as IR
import numpy as np


def _sub_param_fn(plambda, params):
    """
    For processing the params, check the index of params
    """
    if plambda is not None:
        sub_param = []
        for plam in to_list(plambda):
            if callable(plam):
                if isinstance(plam, functools.partial):
                    # The Circuit.to_gate param function is different from the normal lambda function.
                    # The list should convert to np.ndarray and the params should be tuple, i.e., plam((params,))).
                    if isinstance(params, list):
                        params = np.array(params, dtype=object)
                    sub_param.append(plam((params,)))
                else:
                    # The lambda functions
                    sub_param.append(plam(params))
            else:
                # The numeric params
                sub_param.append(plam)
        return to_list(sub_param)

    else:
        return []


def is_primary_gate(gate: Gate):
    # if gate.label == U.label or gate == U:
    #     return False
    if gate in IR.basis_set or gate.label in IR.label_set:
        return True
    elif isinstance(gate, MatrixGate):
        return True
    elif isinstance(gate, ControlledGate) and (isinstance(gate.base_gate, MatrixGate) or
                gate.base_gate in IR.basis_set):
        return True
    elif isinstance(gate, InverseGate) and isinstance(gate.base_gate, MatrixGate): 
    # or gate.base_gate in IR.basis_set):
        return True
    return False


def decompose_single_qubit_gate(gate: Gate, qubits: List, params=[]) -> List:
    """
    Args:
        gate: class `Gate`
        qubits: List, The qubit list which contains qubits that gate applied on
        params: Optional[float,callable], default to None, params are only callable function or (int, float, numpy dtype)

    Return:
        List of Instruction
    """
    decomposition = []
    if len(gate.factors) > 0:
        for f in gate.factors:
            plambda = f[2] if len(f)>2 else None
            sub_params = _sub_param_fn(plambda, params)
            if is_primary_gate(f[0]):
                decomposition.append(Instruction(f[0], qubits, [], *sub_params))
            else:
                decomposition.extend(decompose_single_qubit_gate(f[0], qubits, sub_params))
    else:
        if gate in IR.basis_set or gate.label in IR.label_set:
            decomposition.append(Instruction(gate, qubits, [], params))
        else:
            mat = gate.get_matrix(*params)
            if mat is None:
                raise UnsupportedGateError(gate.label + ' is not supported. Its matrix representation is None.')
            alpha, beta, gamma, phase = decompose_zyz(mat)
            decomposition.append(Instruction(Rz, qubits, [], alpha))
            decomposition.append(Instruction(Ry, qubits, [], beta))
            decomposition.append(Instruction(Rz, qubits, [], gamma))

    return decomposition

def decompose_multi_qubit_gate(gate: Gate, qubits: List, params=[]) -> List:
    if len(gate.factors) > 0:
        decomposition = []
        for f in gate.factors:
            sub_qubits = [qubits[i] for i in f[1]]
            plambda = f[2] if len(f)>2 else None
            sub_params = _sub_param_fn(plambda, params)
            if is_primary_gate(f[0]):
                decomposition.append(Instruction(f[0], sub_qubits, [], *sub_params))
            elif f[0].qubit_num == 1:
                decomposition.extend(decompose_single_qubit_gate(f[0], sub_qubits, sub_params))
            else:
                decomposition.extend(decompose_multi_qubit_gate(f[0], sub_qubits, sub_params))
        return decomposition

    raise UnsupportedGateError(gate.label + ' is not supported.')
