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
from copy import deepcopy
from typing import List

import numpy as np
from igraph import Graph
from scipy import sparse

from .backend_util import get_graph_capsule, _add_pauli_gate
from spinqit.compiler import IntermediateRepresentation, NodeType
from spinqit.model import Instruction
from spinqit.model import I, H, X, Y, Z, Rx, Ry, Rz, T, Td, S, Sd, P, CX, CY, CZ, SWAP, CCX, U
from spinqit.spinq_backends import BasicSimulator

from .basebackend import BaseBackend
from ..primitive import PauliBuilder, calculate_pauli_expectation
from ..utils.function import _flatten
from spinqit.grad import parameter_shift, adjoint_differentiation


class BasicSimulatorConfig:
    def __init__(self):
        self.metadata = {}

    def configure_shots(self, shots: int):
        self.metadata['shots'] = shots

    def configure_measure_qubits(self, mqubits: List):
        self.metadata['mqubits'] = mqubits

    def configure_print_circuit(self, verbose: bool = True):
        self.metadata['print_circuit'] = verbose


class BasicSimulatorBackend(BaseBackend):
    def __init__(self,):
        super().__init__()

        self.simulator = BasicSimulator()

    def assemble(self, ir: IntermediateRepresentation):
        i = 0
        while i < ir.dag.vcount():
            v = ir.dag.vs[i]
            if v['type'] == NodeType.op.value or v['type'] == NodeType.callee.value:
                if v['name'] == SWAP.label:
                    qubits, clbits = self.__qubits_and_clbits(v)
                    subgates = []
                    for sg, qidx in SWAP.factors:
                        subgates.append(Instruction(sg, [qubits[i] for i in qidx], clbits))
                    ir.substitute_nodes([v.index], subgates, v['type'])
                    ir.remove_nodes([v.index], False)
                    i -= 1
                elif v['name'] == U.label:
                    qubits, clbits = self.__qubits_and_clbits(v)
                    if v['type'] == NodeType.op.value:
                        subgates = []
                        for sg, qidx, pexp in U.factors:
                            subgates.append(Instruction(sg, [qubits[i] for i in qidx], clbits, pexp(v['params'])))
                        ir.substitute_nodes([v.index], subgates, v['type'])
                        ir.remove_nodes([v.index], False)
                    else:
                        self.__substitute_callee_U(v, ir, qubits, clbits)
                    i -= 1
                elif v['name'] == CX.label:
                    v['name'] = 'CNOT'
                elif v['name'] == CY.label:
                    v['name'] = 'YCON'
                elif v['name'] == CZ.label:
                    v['name'] = 'ZCON'
                elif v['name'] == CCX.label:
                    v['name'] = 'CCX'
            i += 1

    def execute(self, ir: IntermediateRepresentation, config, state=None, params=None):
        if params is not None:
            self.update_param(ir, params)
        self.assemble(ir)
        return self.simulator.execute(get_graph_capsule(ir.dag), config.metadata)

    def expval(self, ir, config, hamiltonian, state=None, params=None,):
        value = 0.0
        if isinstance(hamiltonian, (np.ndarray, sparse.csr_matrix)):
            result = self.execute(ir, config, state=state, params=params)
            if not result.states:
                raise ValueError(
                    f'The state is empty, may not use `type:{type(hamiltonian)}` hamiltonian. '
                    f'Instead use `type:list` hamiltonian.'
                )
            psi = np.array(result.states)
            value = np.real(psi.conj() @ hamiltonian @ psi)
        elif isinstance(hamiltonian, list):
            mqubits = config.metadata['mqubits'] if 'mqubits' in config.metadata else list(range(ir.qnum))
            for i, (pstr, coeff) in enumerate(hamiltonian):
                h_part = PauliBuilder(pstr).to_gate()
                execute_ir = deepcopy(ir)
                _add_pauli_gate(h_part, mqubits, execute_ir)
                result = self.execute(execute_ir, config, state=state, params=params)
                value += coeff * calculate_pauli_expectation(pstr, result.probabilities)
        return value

    def grads(self, ir, params, hamiltonian, config, method, state=None):
        if method == 'backprop':
            raise ValueError(f'The `backprop` method are not supported on the {self.__class__.__name__}.'
                             'Choose other method or use `TorchSimulatorBackend`')
        if method == 'param_shift':
            grad_func = parameter_shift
        elif method == 'adjoint_differentiation':
            if isinstance(hamiltonian, list):
                raise ValueError(
                    f'The hamiltonian is `type:{type(hamiltonian)}`, '
                    f'may use `spinqit.generate_hamiltonian_matrix`'
                )
            grad_func = adjoint_differentiation
        else:
            raise ValueError(f'The method {method} are not supported for basic backend now')
        loss, grads = grad_func(ir, config, params, hamiltonian, self, state)
        return loss, grads

    @staticmethod
    def update_param(ir, new_params):
        """
        Updating the trainable params
        """
        for v in ir.dag.vs:
            if 'trainable' in v.attributes() and v['trainable']:
                func = v['trainable']
                v['params'] = list(_flatten((func(new_params).tolist(),)))

    @staticmethod
    def __qubits_and_clbits(v):
        edges = v.in_edges()
        edges.sort(key=lambda k: k.index)
        qubits = []
        clbits = []
        for e in edges:
            if 'qubit' in e.attributes() and e['qubit'] is not None:
                qubits.append(e['qubit'])
            elif 'clbit' in e.attributes() and e['clbit'] is not None:
                clbits.append(e['clbit'])
        return qubits, clbits

    @staticmethod
    def __substitute_callee_U(v, ir, qubits, clbits):
        subgates = []
        pindex_group = []
        var_full = v['pindex']
        start = 0
        for func in v['params']:
            arg_count = func.__code__.co_argcount
            var_slice = [] if arg_count == 0 else var_full[start:start + arg_count]
            pindex_group.append(var_slice)
            start += arg_count
        subgates.append(Instruction(Rz, qubits, clbits, v['params'][2]))
        subgates.append(Instruction(Ry, qubits, clbits, v['params'][0]))
        subgates.append(Instruction(Rz, qubits, clbits, v['params'][1]))
        new_nodes = ir.substitute_nodes([v.index], subgates, v['type'])
        nv1 = ir.dag.vs[new_nodes[0]]
        nv1['pindex'] = pindex_group[2]
        nv2 = ir.dag.vs[new_nodes[1]]
        nv2['pindex'] = pindex_group[0]
        nv3 = ir.dag.vs[new_nodes[2]]
        nv3['pindex'] = pindex_group[1]
        ir.remove_nodes([v.index], False)
        return subgates
