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
#
# This file is based on the implementation in https://github.com/1ucian0/rpo.
# The original notice is as follows.
#
# (C) Copyright Ji Liu and Luciano Bello 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from typing import List
from ..ir import IntermediateRepresentation, NodeType
from .util import get_qubits
from spinqit.model import Instruction
from spinqit.model import S, Sd, T, Td, H, X, Y, Z, CX, CY, CZ, SWAP, CCX 



class ConstantsStateOptimization(object):
    controlled_gates = {CX.label, CY.label, CZ.label, CCX.label} 
    nothing_gates = {S, T, Sd, Td}
    swap_rules = {
        ('0', '-'): [(X, [0]), (H, [0]), (H, [1]), (X, [1])],
        ('1', '+'): ('0', '-'),
        (None, '-'): [(Z, [0]), (CX, [1, 0]), (CX, [0, 1])],
        ('-', None): [(Z, [1]), (CX, [0, 1]), (CX, [1, 0])],
        ('1', None): [(X, [1]), (CX, [1, 0]), (CX, [0, 1])],
        (None, '1'): [(X, [0]), (CX, [0, 1]), (CX, [1, 0])],
        ('+', '-'): [(Z, [0]), (Z, [1])],
        ('-', '+'): ('+', '-'),
        ('+', None): (None, '0'),
        (None, '0'): [(CX, [0, 1]), (CX, [1, 0])],
        ('0', None): (None, '+'),
        (None, '+'): [(CX, [1, 0]), (CX, [0, 1])],
         ('0', '1'): ('1', '0'),
        ('1', '0'): [(X, [0]), (X, [1])],
        ('0', '+'): [(H, [0]), (H, [1])],
        ('+', '0'): ('0', '+'),
        ('1', '-'): ('0', '+'),
        ('-', '1'): ('0', '+'),
        ('-', '0'): ('+', '1'),
        ('+', '1'): [(H, [0]), (X, [0]), (X, [1]), (H, [1])]
    }

    def __init__(self):
        self.wire_state = None

    def run(self, ir: IntermediateRepresentation):
        self.wire_state = BasisState(ir.dag['qnum'])

        to_delete = []
        vs = ir.dag.topological_sorting()
        for v in vs:
            if ir.dag.vs[v]['type'] == NodeType.caller.value:
                break
            if ir.dag.vs[v]['type'] == NodeType.op.value:
                if 'cmp' in ir.dag.vs[v].attributes() and ir.dag.vs[v]['cmp'] is not None:
                    break
                gname = ir.dag.vs[v]['name']
                qargs = ir.dag.vs[v]['qubits']
                
                if gname in self.controlled_gates:
                    if gname == CX.label and self.wire_state[qargs[-1]] == '+':
                        to_delete.append((v, True)) 
                        continue
                    
                    ctrl_qubits = qargs[:-1]
                    ctrl_state = '11' if len(ctrl_qubits) ==2 else '1'
                    new_state = ''
                    new_ctrl_qubits = []
                    for qubit, state in zip(ctrl_qubits, ctrl_state):
                        if self.wire_state[qubit] in [None, '+', '-']:
                            new_state += state
                            new_ctrl_qubits.append(qubit)
                        elif self.wire_state[qubit] != state:
                            to_delete.append((v, True))
                            break
                    else:
                        if self.wire_state[qargs[-1]] == '-':
                            if not new_ctrl_qubits and self.wire_state[qargs[0]] in ['0', '1']:
                                to_delete.append((v, True))
                                continue
                            else:
                                new_dag = self.z_dag(new_state, new_ctrl_qubits)
                        else:
                            if ctrl_state == new_state and ctrl_qubits == new_ctrl_qubits:
                                self.constant_analysis([gname], [qargs])
                                continue

                            new_dag = self.toffoli_dag(gname, qargs, new_state, new_ctrl_qubits)
                        new_ops = [i.get_op() for i in new_dag]
                        wires = [i.qubits for i in new_dag]
                        self.constant_analysis(new_ops, wires)
                        ir.substitute_nodes([v], new_dag, ir.dag.vs[v]['type'])
                        to_delete.append((v, False))
                elif gname == SWAP.label:
                    if self.wire_state[qargs[0]] == self.wire_state[qargs[1]] is None:
                        continue
                    if self.wire_state[qargs[0]] == self.wire_state[qargs[1]]:
                        to_delete.append((v, True))
                        continue
                    new_dag = self.swap_dag(qargs)

                    ir.substitute_nodes([v], new_dag, ir.dag.vs[v]['type'])
                    to_delete.append((v, False))
                    self.wire_state.swap(qargs[0], qargs[1])
                else:
                    self.constant_analysis([gname], [qargs])
        
        keep_list = []
        non_keep_list = []
        for element in to_delete:
            if element[1] == True:
                keep_list.append(element[0])
            else:
                non_keep_list.append(element[0])
        ir.remove_nodes(keep_list, True)
        ir.remove_nodes(non_keep_list, False)
                
    def constant_analysis(self, nodes: List, wires: List):
        '''Update wire states'''
        for i in range(len(nodes)):
            node = nodes[i]
            if isinstance(node, str):
                node = IntermediateRepresentation.get_basis_gate(node)
            qargs = wires[i]
            if node in self.wire_state.available_rules:
                self.wire_state[qargs[0]] = node
            elif node in self.nothing_gates:
                continue
            else:
                for qarg in qargs:
                    self.wire_state[qarg] = None

    @staticmethod
    def toffoli_dag(gate: str, qargs: List, state: str, ctrl_qubits: List) -> List:
        new_dag = []
        if len(state):
            qubits = ctrl_qubits
            qubits.append(qargs[-1])
            new_dag.append(Instruction(CX, qubits, []))
        else:
            if gate == CX.label:
                new_gate = X
            elif gate == CY.label:
                new_gate = Y
            elif gate == CZ.label:
                new_gate = Z
            new_dag.append(Instruction(new_gate, [qargs[-1]], []))
        return new_dag

    @staticmethod
    def z_dag(state: str, ctrl_qubits: List):
        new_dag = []
        if len(state) == 1:
            new_dag.append(Instruction(Z, ctrl_qubits, []))
        else:
            new_dag.append(Instruction(CZ, ctrl_qubits, []))
        return new_dag

    def swap_dag(self, qargs: List):
        new_dag = []
        states = (self.wire_state[qargs[0]], self.wire_state[qargs[1]])
        rules = ConstantsStateOptimization.get_swap_rules(states)

        for rule in rules:
            sub_args = [qargs[i] for i in rule[1]]
            new_dag.append(Instruction(rule[0], sub_args, []))
        return new_dag

    @staticmethod
    def get_swap_rules(states):
        rules = ConstantsStateOptimization.swap_rules.get(states)
        if isinstance(rules, tuple):
            rules = ConstantsStateOptimization.swap_rules.get(rules)
        return rules


class BasisState():
    rules = {H: {'0': '+', '1': '-', '+': '0', '-': '1'},
             Z: {'0': '0', '1': '1', '+': '-', '-': '+'},
             X: {'0': '1', '1': '0', '+': '+', '-': '-'},
             Y: {'0': '1', '1': '0', '+': '-', '-': '+'}
    }

    def __init__(self, qnum: int):
        self._dict = {q: '0' for q in range(qnum)}

    def __setitem__(self, key: int, item: str):
        rule = self.rules.get(item)
        if rule:
            if self._dict[key] is not None:
                self._dict[key] = rule[self._dict[key]]
        else:
            self._dict[key] = item

    def __getitem__(self, key: int):
        return self._dict[key]

    def __repr__(self):
        return repr(self._dict)

    def swap(self, qubit1: int, qubit2: int):
        self._dict[qubit1], self._dict[qubit2] = self._dict[qubit2], self._dict[qubit1]

    @property
    def available_rules(self):
        return self.rules.keys()