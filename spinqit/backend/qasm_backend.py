# Copyright 2022 SpinQ Technology Co., Ltd.
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
from collections import defaultdict
from copy import deepcopy

import numpy as onp
from scipy import sparse

from spinqit import CP
from spinqit.compiler.ir import NodeType

from .backend_util import _add_pauli_gate
from ..model.parameter import LazyParameter
from ..primitive import PauliBuilder, calculate_pauli_expectation
from ..utils.function import _flatten, requires_grad
from autoray import numpy as ar
from spinqit.grad import grad_func_spinq

comparator_map = {
    0: '==',
    1: '!=',
    2: '<',
    3: '>',
    4: '<=',
    5: '>='
}

gate_name = {
    'sd': 'sdg',
    'td': 'tdg',
    'i': 'id',
    CP.label.lower(): 'cp'
}


class QasmConfig:
    def __init__(self, shots=1024, mqubits=None):
        self.shots = shots
        self.mqubits = mqubits

    def configure_shots(self, shots: int):
        self.shots = shots

    def configure_measure_qubits(self, mqubits):
        self.mqubits = mqubits


class QiskitQasmResult:
    def __init__(self, ):
        self.states = onp.array([])
        # For lazy evaluation
        self.counts_fn = None
        self.probabilities_fn = None

    def __str__(self):
        return f'Counts: {self.counts}, States: {self.states}, Prob: {self.probabilities}'

    def set_result(self, res, shots):
        if isinstance(res, dict):
            self.counts_fn = lambda: {k[::-1]: v for k, v in res.items()}
            self.probabilities_fn = lambda: {k: v / shots for k, v in self.counts.items()}
        else:
            self.states = res.reshape([2] * int(onp.log2(res.shape[0]))).T.reshape(-1).tolist()

            def prob_fn():
                np_states = onp.abs(res) ** 2
                prob = {}
                for i, v in enumerate(np_states):
                    prob[(bin(i)[2:])] = v
                return prob
            self.probabilities_fn = prob_fn
            self.counts_fn = lambda: {k: v * shots for k, v in self.probabilities.items()}

    @property
    def counts(self):
        return self.counts_fn()

    @property
    def probabilities(self):
        return self.probabilities_fn()

    def get_random_reading(self):
        return onp.random.choice(list(self.counts.keys()))


class QasmBackend:
    """
    The QasmBackend convert ir to the *.qasm.

    Args:
        fn (Callable): The executor must be able to execute the qasm circuit.

    """

    def __init__(self, fn):
        self.executor = fn
        # self.result = QasmResult()

    def execute(self, ir, config):
        shots = config.shots
        qasm_str = self.convert_ir_to_qasm(ir)
        res = self.executor(qasm_str, shots)
        return res

    @staticmethod
    def process_params(new_params, ):
        execute_params = []
        for param in new_params:
            execute_params.append(ar.asarray(param, like='spinq', trainable=requires_grad(param)))
        return execute_params

    @functools.lru_cache
    def check_node(self, ir, place_holder):

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
            mqubits = config.mqubits if config.mqubits is not None else list(range(ir.qnum))
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
                value = onp.real(psi.conj() @ hamiltonian @ psi)
            elif measure_op.mtype == 'prob':
                if 'mqubits' in config.metadata:
                    np_probs = onp.zeros(2 ** (len(config.metadata['mqubits'])))
                else:
                    np_probs = onp.zeros(2 ** ir.qnum, dtype=float)
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
    def convert_ir_to_qasm(ir):
        qasm_content = ''

        qasm_content += 'OPENQASM 2.0;\n'
        qasm_content += 'include "qelib1.inc";\n'
        edges = defaultdict(list)
        for u, v in ir.edges:
            if v not in edges[u]:
                edges[u].append(v)

        # Before the qreg are the `qelib1.inc` callee node,
        qreg_dict = {}
        creg_dict = {}
        visited = set()
        for i in range(ir.dag.vcount()):
            v = ir.dag.vs[i]
            if i in visited or i in ir.include_gate:
                continue
            if v['type'] == NodeType.register.value:
                register, num = v['name'].split('_')
                args = register[0]
                qasm_content += f'{args}reg {register}[{int(num)}];\n'
            elif v['type'] == NodeType.init_qubit.value:
                register, _, idx = v['name'].split('_')
                qreg_dict[int(idx) + int(register[1:])] = (register, int(idx))
            elif v['type'] == NodeType.init_clbit.value:
                register, _, idx = v['name'].split('_')
                creg_dict[int(idx) + int(register[1:])] = (register, int(idx))
            elif v['type'] == NodeType.definition.value:
                gate = v['name'].lower()
                if gate not in gate_name:
                    qubits = v['qubits']
                    param_num = v['params']
                    qargs = []
                    pargs = []
                    qasm_content += f'gate {gate}'
                    if param_num > 0:
                        qasm_content += ' ('
                        for j in range(param_num):
                            pargs.append(f'a{j}')
                        qasm_content += ','.join(pargs) + ')'
                    for j in range(qubits):
                        if j == qubits - 1:
                            qasm_content += f' qb{j}\n'
                        else:
                            qasm_content += f' qb{j},'
                        qargs.append(f'qb{j}')
                    qasm_content += '{\n'

                    edge = edges[i]
                    while edge:
                        idx = edge[0]
                        _v = ir.dag.vs[idx]
                        if _v['type'] != 1 and _v['type'] != 3:
                            raise ValueError
                        conbits = [creg_dict[i][0] for i in ir.get_conbits(i)]
                        if 'cmp' in v.attributes() and v['cmp'] is not None:
                            relation = comparator_map[v['cmp']]
                            qasm_content += f'if ({conbits[0]}{relation}{v["constant"]}) '
                        _gate = _v['name'].lower()
                        _gate = gate_name.get(_gate, _gate)
                        qubits = [qargs[i] for i in _v['qubits']]
                        param = _v['params']
                        if 'pindex' in _v.attributes() and _v['pindex'] is not None:
                            start = 0
                            _v_pargs = []
                            for f in param:
                                arg_count = f.__code__.co_argcount
                                if arg_count == 0:
                                    _v_pargs.append(str(f()))
                                else:
                                    _v_pargs.append(list(pargs[i] for i in _v['pindex'][start:start + arg_count]))
                                    start += arg_count
                            if _v['expression'] is None:
                                _v_expression = sum(_v_pargs, [])
                            else:
                                expression_list = _v['expression']
                                _v_expression = []
                                for i, expression in enumerate(expression_list):
                                    func = eval(expression)
                                    _v_expression.append(func(*_v_pargs[i]))
                            qasm_content += f'{_gate}({",".join(_v_expression)}) {",".join(qubits)};\n'
                        else:
                            qasm_content += f'{_gate} {",".join(qubits)};\n'
                        edge = edges[idx]
                        visited.add(idx)

                    qasm_content += '}\n'
            elif v['type'] == NodeType.op.value:
                conbits = [creg_dict[i][0] for i in ir.get_conbits(i)]
                if 'cmp' in v.attributes() and v['cmp'] is not None:
                    relation = comparator_map[v['cmp']]
                    qasm_content += f'if ({conbits[0]}{relation}{v["constant"]}) '
                gate = v['name'].lower()
                gate = gate_name.get(gate, gate)
                qubits = [qreg_dict[i] for i in v['qubits']]
                if gate == 'measure':
                    clbits = [creg_dict[i] for i in ir.get_clbits(i)]
                    for (q, q_idx), (c, c_idx) in zip(qubits, clbits):
                        qasm_content += f'{gate} {q}[{q_idx}] -> {c}[{c_idx}];\n'
                else:
                    param = v['params'] if 'params' in v.attributes() else None
                    if not param:
                        qubits = [f'{q[0]}[{q[1]}]' for q in qubits]
                        qasm_content += f'{gate} {",".join(qubits)};\n'
                    else:
                        qubits = [f'{q[0]}[{q[1]}]' for q in qubits]
                        qasm_content += f'{gate}({",".join(map(str, param))}) {",".join(qubits)};\n'
            elif v['type'] == NodeType.caller.value:
                conbits = [creg_dict[i][0] for i in ir.get_conbits(i)]
                if 'cmp' in v.attributes() and v['cmp'] is not None:
                    relation = comparator_map[v['cmp']]
                    qasm_content += f'if ({conbits[0]}{relation}{v["constant"]}) '
                gate = v['name'].lower()
                gate = gate_name.get(gate, gate)
                qubits = [f'{qreg_dict[i][0]}[{qreg_dict[i][1]}]' for i in v['qubits']]
                param = v['params']
                if not param:
                    qasm_content += f'{gate} {",".join(qubits)};\n'
                else:
                    qasm_content += f'{gate}({",".join(map(str, param))}) {",".join(qubits)};\n'
            visited.add(i)
        return qasm_content

    @staticmethod
    def save_file(qasm_str, file_name):
        onp.savetxt(fname=file_name, X=qasm_str)
