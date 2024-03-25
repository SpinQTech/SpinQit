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
from typing import Union, Tuple
import re
from numpy import pi, sqrt
from sympy import Symbol, symbols, to_cnf, simplify
from sympy.logic.boolalg import And, Or, Not
from sympy.parsing.sympy_parser import parse_expr
from spinqit import Gate, GateBuilder, Circuit
from spinqit import get_compiler, check_backend_and_config
from spinqit import H, X, CX, MultiControlledGateBuilder, RepeatBuilder
from spinqit.primitive import AmplitudeAmplification


class SATSolver:
    def __init__(self, expr: Union[str, And], ):
        if isinstance(expr, str):
            self.expr = self.to_sym_expr(expr)
        elif isinstance(expr, And):
            self.expr = expr
        self.expr = to_cnf(self.expr)
        self.circuit = self.build_circuit()

    def to_sym_expr(self, str_expr: str):
        variables = set(re.findall(r'[a-zA-Z]', str_expr))
        locals = {v: symbols(v) for v in variables}
        expr = parse_expr(str_expr, local_dict={**locals, 'And': And, 'Or': Or, 'Not': Not})

    def calc_qubit_number(self) -> Tuple:
        sym_set = self.expr.atoms(Symbol)
        self.symbols_in_expr = dict()
        for idx, el in enumerate(sym_set):
            self.symbols_in_expr[el] = idx
        sym_num = len(sym_set)
        self.clauses = [clause for clause in self.expr.args if isinstance(clause, Or)]
        clauses_num = len(self.clauses)
        return sym_num, clauses_num

    def construct_oracle(self, qubit_number) -> Gate:
        oracle_builder = GateBuilder(qubit_number)
        uncomputation = []
        for cidx, clause in enumerate(self.clauses):
            arg_num = len(clause.args)
            clause_builder = GateBuilder(arg_num + 1)
            ex_indices = []
            not_indices = []
            if arg_num > 1:
                not_indices.append(cidx)
                for idx, elem in enumerate(clause.args):
                    if not isinstance(elem, Not):
                        qindex = self.symbols_in_expr[elem]
                        clause_builder.append(X, [idx])
                    else:
                        elem_sym = elem.args[0]
                        qindex = self.symbols_in_expr[elem_sym]
                    ex_indices.append(qindex)

                mcx_builder = MultiControlledGateBuilder(arg_num, X)
                clause_builder.append(mcx_builder.to_gate(), list(range(arg_num+1)))
                for idx, elem in enumerate(clause.args):
                    if not isinstance(elem, Not):
                        clause_builder.append(X, [idx])
            else:
                qindex = self.symbols_in_expr[clause.args[0]]
                ex_indices.append(qindex)
                if isinstance(clause, Not):
                    clause_builder.append(X, [0])
                    clause_builder.append(CX, [0,1])
                    clause_builder.append(X, [0])
                else:
                    clause_builder.append(CX, [0,1])            
            clause_gate = clause_builder.to_gate()
            oracle_builder.append(clause_gate, ex_indices + [len(self.symbols_in_expr) + cidx])
            uncomputation.append((clause_gate, ex_indices + [len(self.symbols_in_expr) + cidx]))
        
        for nidx in not_indices:
            oracle_builder.append(X, [len(self.symbols_in_expr) + nidx])
        con_builder = MultiControlledGateBuilder(len(self.clauses), X)
        con_indices = [len(self.symbols_in_expr) + i for i in range(len(self.clauses)+1)]
        oracle_builder.append(con_builder.to_gate(), con_indices)
        for nidx in not_indices:
            oracle_builder.append(X, [len(self.symbols_in_expr) + nidx])

        for ungate, unindices in uncomputation[::-1]:
            oracle_builder.append(ungate, unindices)
        return oracle_builder.to_gate()

    def build_circuit(self) -> Circuit:
        circ = Circuit()
        sym_num, clauses_num = self.calc_qubit_number()
        sym_reg = circ.allocateQubits(sym_num)
        inter_reg = circ.allocateQubits(clauses_num)
        result_reg = circ.allocateQubits(1)

        total_qnum = sym_num + clauses_num + 1
        oracle = self.construct_oracle(total_qnum)
        state_op = RepeatBuilder(H, sym_num).to_gate()

        grover_insts = AmplitudeAmplification(flip=oracle, flip_qubits=sym_reg+inter_reg+result_reg, state_operator = state_op, state_qubits=sym_reg, reflection_qubits=sym_reg+result_reg).build()

        iterations = int(pi / 4 * sqrt(2 ** sym_num))
        for i in range(iterations):
            circ.extend(grover_insts)
        return circ

    def solve(self, backend_mode, **kwargs):
        self.backend, self.config = check_backend_and_config(backend_mode, **kwargs)
        circ = self.build_circuit()
        compiler = get_compiler()
        optimization_level = 1
        exe = compiler.compile(circ, optimization_level)
        self.config.configure_measure_qubits(list(range(len(self.symbols_in_expr))))
        result = self.backend.execute(exe, self.config)
        pairs = sorted(result.probabilities.items(), key=lambda d: d[1], reverse=True)
        for key, _ in pairs:
            values = [True if d=='1' else False for d in key]
            assignment = {k:v for k, v in zip(self.symbols_in_expr, values)}
            res = self.expr.subs(assignment)
            simplified_result = simplify(res)
            if simplified_result == True:
                return assignment
        print('There is no solution for this SAT problem.')
    