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

from .backend_util import _basis_rotation_ir
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
            for pstr, coeff in hamiltonian:
                measurement_ir = _basis_rotation_ir(pstr, mqubits, ir)
                result = self.execute(measurement_ir, config)
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
        graph = ir.dag
        order = graph.topological_sorting()
        lines = ['OPENQASM 2.0;', 'include "qelib1.inc";']
        qregs, cregs = {}, {}
        for v in graph.vs:
            if v['type'] == NodeType.register.value:
                register, size = v['name'].split('_')
                lines.append('{}reg {}[{}];'.format(register[0], register, size))
            elif v['type'] in (NodeType.init_qubit.value, NodeType.init_clbit.value):
                prefix = v['name'][0]
                start, size, offset = map(int, v['name'][1:].split('_'))
                mapping = qregs if prefix == 'q' else cregs
                mapping[start + offset] = (prefix + str(start), offset)

        def condition(v):
            if v.attributes().get('cmp') is None:
                return ''
            bits = ir.get_conbits(v.index)
            registers = {cregs[b][0] for b in bits}
            if len(registers) != 1:
                raise ValueError('QASM condition must address one complete classical register')
            register = next(iter(registers))
            if bits != sorted(b for b in cregs if cregs[b][0] == register):
                raise ValueError('QASM condition must address one complete classical register')
            return 'if({}{}{}) '.format(register, comparator_map[v['cmp']], v['constant'])

        aliases = dict(gate_name, cnot='cx', ycon='cy', zcon='cz')
        def statement(v, wires, params):
            name = aliases.get(v['name'].lower(), v['name'].lower())
            arguments = '(' + ','.join(map(str, params)) + ')' if params else ''
            return '{}{} {};'.format(name, arguments, ','.join(wires))

        definitions = {v['name']: v.index for v in graph.vs if v['type'] == NodeType.definition.value}
        bodies = {name: set(graph.subcomponent(idx, mode='out')) - {idx}
                  for name, idx in definitions.items()}
        internal = set().union(*bodies.values()) if bodies else set()
        emitted, active = set(), set()
        def emit_definition(name):
            if name in emitted:
                return
            if name in active:
                raise ValueError('Recursive QASM gate definition')
            index = definitions[name]
            if index in ir.include_gate:
                emitted.add(name)
                return
            active.add(name)
            body = [i for i in order if i in bodies[name]]
            for i in body:
                v = graph.vs[i]
                if v['type'] == NodeType.caller.value:
                    if v['name'] not in definitions:
                        raise ValueError('Missing QASM gate definition: ' + v['name'])
                    emit_definition(v['name'])
            root = graph.vs[index]
            args = ['a{}'.format(i) for i in range(root['params'])]
            wires = ['qb{}'.format(i) for i in range(root['qubits'])]
            signature = '(' + ','.join(args) + ')' if args else ''
            lines.append('gate {}{} {} {{'.format(name.lower(), signature, ','.join(wires)))
            for i in body:
                v = graph.vs[i]
                if v['type'] not in (NodeType.callee.value, NodeType.caller.value):
                    raise ValueError('Unsupported node in QASM gate definition')
                params, offset = [], 0
                expressions = v.attributes().get('expression')
                pindex = v.attributes().get('pindex') or []
                for j, f in enumerate(v.attributes().get('params') or []):
                    if not callable(f):
                        params.append(f)
                        continue
                    count = f.__code__.co_argcount
                    if expressions:
                        selected = [args[k] for k in pindex[offset:offset + count]]
                        params.append(eval(expressions[j])(*selected))
                        offset += count
                    else:
                        # Native definition functions consume a parameter list.
                        import sympy
                        symbols = list(map(sympy.Symbol, args))
                        value = f(symbols) if pindex == [-1] else f(*[symbols[k] for k in pindex[offset:offset+count]])
                        offset += count
                        values = value if isinstance(value, (list, tuple)) else [value]
                        params.extend(str(x).replace('**', '^') for x in values)
                lines.append(statement(v, [wires[q] for q in v['qubits']], params))
            lines.append('}')
            active.remove(name)
            emitted.add(name)
        for name in definitions:
            emit_definition(name)

        for index in order:
            v = graph.vs[index]
            if index in internal or index in ir.include_gate:
                continue
            if v['type'] in (NodeType.register.value, NodeType.init_qubit.value,
                             NodeType.init_clbit.value, NodeType.definition.value):
                continue
            if v['type'] not in (NodeType.op.value, NodeType.caller.value):
                raise ValueError('QASM export requires decomposed gate nodes')
            prefix = condition(v)
            wires = ['{}[{}]'.format(*qregs[q]) for q in v['qubits']]
            if v['name'] == 'MEASURE':
                targets = ['{}[{}]'.format(*cregs[c]) for c in ir.get_clbits(index)]
                if len(wires) != len(targets):
                    raise ValueError('Measurement operand counts differ')
                lines.extend(prefix + 'measure {} -> {};'.format(q, c) for q, c in zip(wires, targets))
            else:
                lines.append(prefix + statement(v, wires, v.attributes().get('params') or []))
        return '\n'.join(lines) + '\n'

    @staticmethod
    def save_file(qasm_str, file_name):
        onp.savetxt(fname=file_name, X=qasm_str)
