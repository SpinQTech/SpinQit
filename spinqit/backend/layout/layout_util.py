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

from typing import List, Tuple, Set
from igraph import Vertex
from spinqit.compiler import IntermediateRepresentation, NodeType
import pdb
from spinqit.model.spinqCloud.circuit import topological_sort_by_dfs

def _visit_caller_node(ir: IntermediateRepresentation, caller: Vertex, qubits: List) -> List[Tuple]:
    def_node = ir.dag.vs.find(caller['name'], type=NodeType.definition.value)
    connections = []
    
    vs = topological_sort_by_dfs([def_node.index], ir.dag)
    for vidx in vs:
        if vidx != def_node.index:
            node = ir.dag.vs[vidx]
            qidxes = node['qubits']
            local = [qubits[i] for i in qidxes]
            
            if node['type'] == NodeType.callee.value:
                if len(node['qubits']) >= 2:
                    pairs = [(local[i], local[j]) for i in range(len(local)) for j in range(i+1, len(local))]
                    for pair in pairs:
                        connections.append(((caller.index, node.index), pair))
                else:
                    connections.append(((caller.index, node.index), tuple(local)))
            elif node['type'] == NodeType.caller.value:
                recurs = _visit_caller_node(ir, node, local)
                for ids, pair in recurs:
                    connections.append(((caller.index,)+ids, pair))            
    
    return connections

def collect_gate_qubits(ir: IntermediateRepresentation) -> List[Tuple]:
    gates = []

    registers = ir.dag.vs.select(type = NodeType.register.value)
    reg_indices = [node.index for node in registers]
    vidx_list = topological_sort_by_dfs(reg_indices, ir.dag)
    
    for idx in vidx_list:
        v = ir.dag.vs[idx]
        if v['type'] in [NodeType.op.value, NodeType.caller.value]:
            qubits = tuple(v['qubits'])
            if v['type'] == NodeType.op.value:
                gates.append((idx, qubits))  
            elif v['type'] == NodeType.caller.value:
                gates.extend(_visit_caller_node(ir, v, qubits))              
    return gates

    
    




