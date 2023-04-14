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

from spinqit.compiler.decomposer.magic_basis_decomposer import decompose_two_qubit_gate
from igraph import Graph
from ..decomposer import decompose_two_qubit_gate
from ..ir import IntermediateRepresentation, NodeType
from .util import get_paths, get_matrix, get_qubits

def two_qubit_filter(v: int, g: Graph):
    if 'cmp' in g.vs[v].attributes() and g.vs[v]['cmp'] is not None:
        return False
    type = g.vs[v]['type']
    tflag = (type == NodeType.op.value or type == NodeType.callee.value)
    edges = g.vs[v].in_edges()
    eflag = (len(edges) == 2) 
    if eflag:
        if 'qubit' in edges[0].attributes() and edges[0].source == edges[1].source:
            eflag = True
        else:
            successors = g.successors(v)
            if len(successors) != 2 or successors[0] != successors[1]:
                eflag = False
    return tflag and eflag

class CollapseTwoQubitGates(object):
    def __init__(self) -> None:
        pass

    def run(self, ir: IntermediateRepresentation):
        paths = get_paths(ir.dag, two_qubit_filter)
        for path in paths:
            if len(path) > 6:
                node = ir.dag.vs[path[0]]
                qargs = node['qubits']
                op_matrix = get_matrix(node['name'], [0])
                first_qubit = qargs[0] if qargs[0] < qargs[1] else qargs[1]

                for index in path[1:]:
                    node = ir.dag.vs[index]
                    qubits = node['qubits']
                    if first_qubit == qubits[0]:
                        op_matrix = get_matrix(node['name'], [0]).dot(op_matrix)
                    else:
                        op_matrix = get_matrix(node['name'], [1]).dot(op_matrix)

                inst_list = decompose_two_qubit_gate(op_matrix, qargs[0], qargs[1])
                ir.substitute_nodes(path, inst_list, ir.dag.vs[path[0]]['type'])

        to_remove = []
        for path in paths:
            if len(path) > 6:
                to_remove.extend(path)
        ir.remove_nodes(to_remove, False)