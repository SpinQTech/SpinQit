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
from collections import defaultdict
from copy import deepcopy

import numpy as np
from scipy import sparse

from spinqit import CP
from spinqit.grad import parameter_shift, adjoint_differentiation
from spinqit.compiler.ir import NodeType

from .backend_util import _add_pauli_gate
from ..primitive import PauliBuilder, calculate_pauli_expectation
from ..utils.function import _flatten

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
        self.counts = {}
        self.states = np.array([])
        self.probabilities = {}

    def __str__(self):
        return f'Counts: {self.counts}, States: {self.states}, Prob: {self.probabilities}'

    def set_result(self, res, shots):
        if isinstance(res, dict):
            self.counts = {k[::-1]: v for k, v in res.items()}
            self.probabilities = {k: v / shots for k, v in self.counts.items()}
        else:
            self.states = res.reshape([2] * int(np.log2(res.shape[0]))).T.reshape(-1)
            np_states = np.abs(res) ** 2
            for i, v in enumerate(np_states):
                self.probabilities[(bin(i)[2:])] = v
            self.counts = {k: v * shots for k, v in self.probabilities.items()}

    def get_random_reading(self):
        return np.random.choice(list(self.counts.keys()))


class QasmBackend:
    """
    The QasmBackend convert ir to the *.qasm.

    Args:
        fn (Callable): The executor must be able to execute the qasm circuit.

    """

    def __init__(self, fn):
        self.executor = fn
        # self.result = QasmResult()

    def execute(self, ir, config, state=None, params=None):
        shots = config.shots
        self.update_param(ir, params)
        qasm_str = self.convert_ir_to_qasm(ir)
        res = self.executor(qasm_str, shots)
        return res

    def expval(self, ir, config, hamiltonian, state=None, params=None):
        value = 0.0
        if isinstance(hamiltonian, (np.ndarray, sparse.csr_matrix)):
            psi = self.execute(ir, config, state=state, params=params).states
            if not psi.tolist():
                raise ValueError(
                    f'The state is empty, may not use `type:{type(hamiltonian)}` hamiltonian. '
                    f'Instead use `type:list` hamiltonian.'
                )
            value = np.real(psi.conj() @ hamiltonian @ psi)
        elif isinstance(hamiltonian, list):
            mqubits = config.mqubits if config.mqubits is not None else list(range(ir.qnum))
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
            raise ValueError(f'The method `{method}` are not supported for {self.__class__.__name__} now')
        loss, grads = grad_func(ir, config, params, hamiltonian, self, state)
        return loss, grads

    @staticmethod
    def update_param(ir, new_params):
        for v in ir.dag.vs:
            if 'trainable' in v.attributes() and not (not v['trainable']):
                func = v['trainable']
                v['params'] = list(_flatten((func(new_params).tolist(),)))

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
        np.savetxt(fname=file_name, X=qasm_str)
