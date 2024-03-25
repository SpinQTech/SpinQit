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
import functools
import time
import numpy as onp
from copy import deepcopy
from math import pi
from scipy import sparse
from autoray import numpy as ar

from .backend_util import get_graph_capsule, _add_pauli_gate
from .basebackend import BaseBackend
from ..utils import requires_grad
from ..primitive import PauliBuilder, calculate_pauli_expectation, pauli_decompose
from spinqit.compiler import IntermediateRepresentation, NodeType
from spinqit.model import Instruction
from spinqit.model import Ry, Rz, Sd, P, CX, CY, CZ, SWAP, CCX, U, MEASURE, StateVector
from spinqit.model.parameter import LazyParameter
from spinqit.spinq_backends import NMR
from spinqit import CircuitOperationValidationError
from spinqit.grad import grad_func_hardware


class NMRConfig:
    def __init__(self):
        self.metadata = {}

    def configure_shots(self, shots: int):
        self.metadata['shots'] = shots

    def configure_ip(self, addr: str):
        self.metadata['ip'] = addr

    def configure_port(self, port: int):
        self.metadata['port'] = port

    def configure_account(self, username: str, password: str):
        self.metadata['username'] = username
        self.metadata['password'] = password

    def configure_task(self, task_name: str, task_desc: str):
        self.metadata['task_name'] = task_name
        self.metadata['task_desc'] = task_desc

    def configure_measure_qubits(self, mqubits: List):
        self.metadata['mqubits'] = mqubits

    def configure_print_circuit(self, verbose: bool = True):
        self.metadata['print_circuit'] = verbose


class NMRBackend(BaseBackend):
    MAX_RETRIES = 3

    def __init__(self):
        self.machine = NMR()

    def assemble(self, ir: IntermediateRepresentation):
        if 'qnum' not in ir.dag.attributes() or ir.dag['qnum'] <= 0 or ir.dag['qnum'] > 3:
            raise Exception('NMR only supports a circuit with 0 to 3 qubits.')
        i = 0
        while i < ir.dag.vcount():
            v = ir.dag.vs[i]
            if v['type'] == NodeType.op.value or v['type'] == NodeType.callee.value:
                if 'cmp' in v.attributes() and v['cmp'] is not None:
                    raise Exception('NMR does not support conditional gates.')
                if v['name'] == MEASURE.label:
                    raise Exception('NMR does not support the MEASURE gate.')
                if v['name'] == SWAP.label:
                    edges = v.in_edges()
                    edges.sort(key=lambda k: k.index)
                    qubits = []
                    clbits = []
                    for e in edges:
                        if 'qubit' in e.attributes() and e['qubit'] is not None:
                            qubits.append(e['qubit'])
                        elif 'clbit' in e.attributes() and e['clbit'] is not None:
                            clbits.append(e['clbit'])
                    subgates = []
                    for sg, qidx in SWAP.factors:
                        subgates.append(Instruction(sg, [qubits[i] for i in qidx], clbits))
                    ir.substitute_nodes([v.index], subgates, v['type'])
                    ir.remove_nodes([v.index], False)
                    i -= 1
                elif v['name'] == U.label:
                    edges = v.in_edges()
                    qubits = []
                    clbits = []
                    for e in edges:
                        if 'qubit' in e.attributes() and e['qubit'] is not None:
                            qubits.append(e['qubit'])
                        elif 'clbit' in e.attributes() and e['clbit'] is not None:
                            clbits.append(e['clbit'])
                    subgates = []

                    if v['type'] == NodeType.op.value:
                        # for sg, qidx, pexp in U.factors:
                        #     subgates.append(Instruction(sg, [qubits[i] for i in qidx], clbits, pexp(v['params'])))
                        subgates.append(Instruction(Rz, qubits, clbits, v['params'][2]))
                        subgates.append(Instruction(Ry, qubits, clbits, v['params'][0]))
                        subgates.append(Instruction(Rz, qubits, clbits, v['params'][1]))
                        ir.substitute_nodes([v.index], subgates, v['type'])
                        ir.remove_nodes([v.index], False)
                    else:
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
                    i -= 1
                elif v['name'] == P.label:
                    v['name'] = Rz.label
                elif v['name'] == Sd.label:
                    v['name'] = Rz.label
                    v['params'] = [-pi / 2]
                elif v['name'] == CX.label:
                    v['name'] = 'CNOT'
                elif v['name'] == CY.label:
                    v['name'] = 'YCON'
                elif v['name'] == CZ.label:
                    v['name'] = 'ZCON'
                elif v['name'] == CCX.label:
                    v['name'] = 'CCX'
                elif v['name'] == StateVector.label:
                    raise CircuitOperationValidationError("Current platform does not support " + v['name'] + " gate.")
            i += 1

    def execute(self, ir: IntermediateRepresentation, config: NMRConfig):
        self.assemble(ir)
        for i in range(NMRBackend.MAX_RETRIES):
            try:
                result = self.machine.execute(get_graph_capsule(ir.dag), config.metadata)
                break
            except Exception as e:
                if i < NMRBackend.MAX_RETRIES - 1:
                    time.sleep(3)
                else:
                    print('Max retries exceeded. Execution failed.')
                    raise 
        return result

    def get_value_and_grad_fn(self, ir, config, measure_op=None, place_holder=None, grad_method=None):
        def value_and_grad_fn(params):
            params_for_grad = self.process_params(params)
            self.check_node(ir, place_holder)
            self.update_param(ir, params_for_grad)
            val, res = self.evaluate(ir, config, measure_op)
            backward_fn = grad_func_hardware(deepcopy(ir), params_for_grad, config, self, measure_op, res, grad_method)
            return val, backward_fn

        return value_and_grad_fn

    def evaluate(self, ir, config, measure_op):
        if measure_op is None:
            raise ValueError(
                'The measure_op should not be None.'
            )
        if measure_op.mqubits is not None:
            config.configure_measure_qubits(measure_op.mqubits)
        
        if measure_op.mtype == 'expval':
            hamiltonian = measure_op.hamiltonian
            if isinstance(hamiltonian, (onp.ndarray, sparse.csr_matrix)):
                if isinstance(hamiltonian, sparse.csr_matrix):
                    hamiltonian = hamiltonian.A
                hamiltonian = pauli_decompose(hamiltonian)
            value = 0.0
            mqubits = config.metadata['mqubits'] if 'mqubits' in config.metadata else list(range(ir.qnum))
            for pstr, coeff in hamiltonian:
                h_part = PauliBuilder(pstr).to_gate()
                node_idx = _add_pauli_gate(h_part, mqubits, ir)
                result = self.execute(ir, config)
                ir.remove_nodes(node_idx)
                value += coeff * calculate_pauli_expectation(pstr, result.probabilities)
            return value, None
        elif measure_op.mtype == 'prob':
            res = self.execute(ir, config)
            if 'mqubits' in config.metadata:
                np_probs = onp.zeros(2 ** (len(config.metadata['mqubits'])))
            else:
                np_probs = onp.zeros(2**ir.qnum, dtype=float)
            for k, v in res.probabilities.items():
                idx = int(k, 2)
                np_probs[idx] = v
            value = np_probs
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
