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

from igraph import Graph
from numpy import *
from ..ir import NodeType, IntermediateRepresentation
from ..decomposer import decompose_zyz
from .util import get_paths, get_matrix
from spinqit.model import Instruction, Ry, Rz

def single_qubit_filter(v: int, g: Graph):
    if 'cmp' in g.vs[v].attributes() and g.vs[v]['cmp'] is not None:
        return False
    type = g.vs[v]['type']
    tflag = (type == NodeType.op.value or type == NodeType.callee.value)
    edges = g.vs[v].in_edges()
    eflag = (len(edges) == 1 and 'qubit' in edges[0].attributes()) and edges[0]['qubit'] is not None
    return tflag and eflag

class CollapseSingleQubitGates(object):
    def __init__(self) -> None:
        pass

    def run(self, ir: IntermediateRepresentation):
        paths = get_paths(ir.dag, single_qubit_filter)
        for path in paths:
            if len(path) > 3:
                node = ir.dag.vs[path[0]]
                if 'params' in node.attributes() and node['params'] is not None:
                        op_matrix = get_matrix(node['name'], node['params'])
                else:
                    op_matrix = get_matrix(node['name'])
                
                for index in path[1:]:
                    node = ir.dag.vs[index]
                    if 'params' in node.attributes() and node['params'] is not None:
                        op_matrix = get_matrix(node['name'], node['params']).dot(op_matrix)
                    else:
                        op_matrix = get_matrix(node['name']).dot(op_matrix)
                alpha, beta, gamma, phase = decompose_zyz(op_matrix)
                qedges = ir.dag.vs[path[0]].in_edges()
                qubit = qedges[0]['qubit']
                inst_list = []
                inst_list.append(Instruction(Rz, [qubit], [], alpha))
                inst_list.append(Instruction(Ry, [qubit], [], beta))
                inst_list.append(Instruction(Rz, [qubit], [], gamma))
                ir.substitute_nodes(path, inst_list, ir.dag.vs[path[0]]['type'])

        to_remove = []
        for path in paths:
            if len(path) > 3:
                to_remove.extend(path) 
        ir.remove_nodes(to_remove, False)

