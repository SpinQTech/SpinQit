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
from copy import deepcopy
from typing import List

import numpy as onp
from autoray import numpy as ar
from scipy import sparse

from .backend_util import get_graph_capsule, _add_pauli_gate
from spinqit.compiler import IntermediateRepresentation, NodeType
from spinqit.model import Instruction
from spinqit.model import I, H, X, Y, Z, Rx, Ry, Rz, T, Td, S, Sd, P, CX, CY, CZ, SWAP, CCX, U
from spinqit.spinq_backends import BasicSimulator

from spinqit.model.parameter import Parameter, LazyParameter
from .basebackend import BaseBackend
from ..primitive import PauliBuilder, calculate_pauli_expectation, amplitude_encoding
from ..utils.function import requires_grad
from spinqit.grad import grad_func_spinq


class BasicSimulatorConfig:
    def __init__(self):
        self.metadata = {}

    def configure_shots(self, shots: int):
        self.metadata['shots'] = shots

    def configure_measure_qubits(self, mqubits: List):
        self.metadata['mqubits'] = mqubits

    def configure_print_circuit(self, verbose: bool = True):
        self.metadata['print_circuit'] = verbose

    def configure_measure_op(self, measure_op):
        self.metadata['measure_op'] = measure_op


class BasicSimulatorBackend(BaseBackend):
    def __init__(self):
        super().__init__()

        self.simulator = BasicSimulator()

    @functools.lru_cache
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
                elif v['name'] == 'StateVector':
                    raise ValueError(
                        f'The {self.__class__.__name__} does not support StateVector.'
                    )
            i += 1

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

    def execute(self, ir: IntermediateRepresentation, config):
        self.assemble(ir)
        return self.simulator.execute(get_graph_capsule(ir.dag), config.metadata)

    def get_value_and_grad_fn(self, ir, config, measure_op=None, place_holder=None, grad_method=None):
        def value_and_grad_fn(params):
            params_for_grad = self.process_params(params)
            self.check_node(ir, place_holder)
            self.update_param(ir, params_for_grad)
            val, res = self.evaluate(ir, config, measure_op)
            backward_fn = grad_func_spinq(deepcopy(ir), params_for_grad, config, self, measure_op, res, grad_method)
            return val, backward_fn

        return value_and_grad_fn

    def evaluate(self, ir, config, measure_op):
        if measure_op is None:
            raise ValueError(
                'The measure_op should not be None.'
            )
        if isinstance(measure_op.hamiltonian, list):
            value = 0.0
            hamiltonian = measure_op.hamiltonian
            mqubits = config.metadata['mqubits'] if 'mqubits' in config.metadata else list(range(ir.qnum))
            for i, (pstr, coeff) in enumerate(hamiltonian):
                h_part = PauliBuilder(pstr).to_gate()
                node_idx = _add_pauli_gate(h_part, mqubits, ir)
                result = self.execute(ir, config)
                ir.remove_nodes(node_idx)
                value += coeff * calculate_pauli_expectation(pstr, result.probabilities)
            return value, None
        else:
            if measure_op.mqubits is not None:
                config.configure_measure_qubits(measure_op.mqubits)
            res = self.execute(ir, config)
            if measure_op.mtype == 'expval':
                hamiltonian = measure_op.hamiltonian
                if not isinstance(hamiltonian, (onp.ndarray, sparse.csr_matrix)):
                    raise ValueError(
                        f'The hamiltonian type is wrong. '
                        f'Expected `np.ndarray, sparse.csr_matrix, list`, but got `{type(hamiltonian)}`'
                    )
                psi = onp.array(res.states)
                value = onp.real(psi.conj().T @ hamiltonian @ psi)
            elif measure_op.mtype == 'prob':
                if 'mqubits' in config.metadata:
                    np_probs = onp.zeros(2 ** (len(config.metadata['mqubits'])))
                else:
                    np_probs = onp.zeros(2**ir.qnum, dtype=float)
                for k, v in res.probabilities.items():
                    idx = int(k, 2)
                    np_probs[idx] = v
                value = np_probs

            elif measure_op.mtype == 'count':
                value = res.counts
            elif measure_op.mtype == 'state':
                value = onp.array(res.states)
            else:
                raise ValueError(
                    f'The wrong measure_op.mtype expected `prob`, `expval`, `count`, `state`, but got {measure_op.mtype}'
                )
            return value, res

    @staticmethod
    def update_param(ir, new_params):
        """
        Updating the trainable params
        """
        if new_params is not None:
            for v in ir.dag.vs:
                if 'func' in v.attributes() and v['func'] is not None:
                    func = v['func']
                    _params = []
                    for f in func:
                        if callable(f):
                            _p = f(new_params)
                        else:
                            _p = f
                        _params.append(_p)
                    v['params'] = _params

    @staticmethod
    def process_params(new_params):
        execute_params = []
        for param in new_params:
            execute_params.append(ar.asarray(param, like='spinq', trainable=requires_grad(param)))
        return execute_params

    @functools.lru_cache
    def check_node(self, ir, place_holder):
        # self.assemble(ir)
        if place_holder is not None:
            for v in ir.dag.vs:
                if v['type'] in [0, 1] and 'params' in v.attributes() and v['params'] is not None \
                        and any(isinstance(p, LazyParameter) for p in v['params']):
                    params = v['params']
                    record_function = []
                    for p in params:
                        if isinstance(p, LazyParameter):
                            record_function.append(p.get_function(place_holder))
                        else:
                            record_function.append(p)
                    v['func'] = record_function if len(record_function) > 0 else None
