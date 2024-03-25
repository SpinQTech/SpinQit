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

from typing import List, Callable
from igraph import *
from spinqit.model import I, H, X, Y, Z, Rx, Ry, Rz, T, Td, S, Sd, P, CX, CY, CZ, SWAP, CCX, U, MEASURE, StateVector
from spinqit.model import Instruction, Gate
import enum
import numpy as np

class NodeType(enum.Enum):
    op = 0
    caller = 1
    definition = 2
    callee = 3
    register = 4
    init_qubit = 5
    init_clbit = 6
    unitary = 7

class Comparator(enum.Enum):
    EQ = 0
    NE = 1
    LT = 2
    GT = 3
    LE = 4
    GE = 5

class IntermediateRepresentation():
    basis_set = {I, H, X, Y, Z, Rx, Ry, Rz, T, Td, S, Sd, P, CX, CY, CZ, SWAP, CCX, MEASURE, StateVector}
    label_set = {g.label for g in basis_set}
    basis_map = {}
    for gate in basis_set:
        basis_map[gate.label] = gate

    @classmethod
    def get_basis_gate(cls, name: str) -> Gate:
        for g in cls.basis_set:
            if name == g.label:
                return g
        if name in cls.basis_map:
            return cls.basis_map[name]
        elif name == 'CNOT':
            return CX
        elif name == 'YCON':
            return CY
        elif name == 'ZCON':
            return CZ
        elif name == 'CCX':
            return CCX
        elif name == 'U':
            return U
        else:
            raise ValueError(
                f'The gate {name} are not a basis gate in IR'
            )

    def __init__(self):
        self.dag = Graph(directed=True)
        self.qnum = 0
        self.cnum = 0
        self.leaves = {}
        self.edges = []
        self.edge_attributes = {}
        self.include_gate = set()

    @staticmethod
    def get_comparator(sym: str):
        if sym == '==':
            return Comparator.EQ.value
        elif sym == '!=':
            return Comparator.NE.value
        elif sym == '<':
            return Comparator.LT.value
        elif sym == '>':
            return Comparator.GT.value
        elif sym == '<=':
            return Comparator.LE.value
        elif sym == '>=':
            return Comparator.GE.value
        else:
            raise ValueError("Unknown comparator " + sym)

    def add_init_nodes(self, start: int, cnt: int, type: NodeType):
        vcount = self.dag.vcount()
        self.dag.add_vertices(cnt + 1)

        if type == NodeType.init_qubit:
            reg_name = f'q{start}_{cnt}'
        else:
            reg_name = f'c{start}_{cnt}'
        
        self.dag.vs[vcount]['type'] = NodeType.register.value
        self.dag.vs[vcount]['name'] = reg_name

        if type == NodeType.init_qubit:
            self.qnum += cnt
        else:
            self.cnum += cnt

        for i in range(cnt):
            self.dag.vs[vcount + 1 + i]['type'] = type.value
            self.dag.vs[vcount + 1 + i]['name'] = reg_name + '_' + str(i)
            self.edges.append((vcount, vcount+1+i))
            if type == NodeType.init_qubit:
                self.leaves[f'q{start+i}'] = vcount + 1 + i
            else:
                self.leaves[f'c{start+i}'] = vcount + 1 + i

    def add_const_node(self, value:int):
        pass

    def add_op_node(self, gatename: str, params: List, qubits: List, clbits: List) -> int:
        self.dag.add_vertices(1)
        index = self.dag.vcount() - 1
        self.dag.vs[index]['type'] = NodeType.op.value
        self.dag.vs[index]['name'] = gatename
        self.dag.vs[index]['qubits'] = qubits
        
        if params is not None and len(params) > 0:
            self.dag.vs[index]['params'] = params

        for i in qubits:
            leaf = self.leaves[f'q{i}']
            self.edges.append((leaf, index))
            self.edge_attributes[len(self.edges)-1] = {"qubit": i}
            self.leaves[f'q{i}'] = index

        for j in clbits:
            leaf = self.leaves[f'c{j}']
            # self.dag.add_edge(leaf, index)
            self.edges.append((leaf, index))
            self.edge_attributes[len(self.edges)-1] = {"clbit": j}
            self.leaves[f'c{j}'] = index

        return index

    def add_def_node(self, gatename: str, param_num: int, qubit_num: int, clbit_num: int):
        self.dag.add_vertices(1)
        index = self.dag.vcount() - 1
        self.dag.vs[index]['type'] = NodeType.definition.value
        self.dag.vs[index]['name'] = gatename
        self.dag.vs[index]['def'] = gatename
        self.dag.vs[index]['params'] = param_num
        self.dag.vs[index]['qubits'] = qubit_num
        self.dag.vs[index]['clbits'] = clbit_num
        
        # reset the leaves map
        for i in range(qubit_num):
            self.leaves[f'_q{i}'] = index

        for j in range(clbit_num):
            self.leaves[f'_c{j}'] = index

    def add_callee_node(self, gatename: str, params: List[Callable], qubits: List[int], 
                        clbits: List[int], param_idx: List[int], is_caller: bool = False, expression=None) -> int:
        self.dag.add_vertices(1)
        index = self.dag.vcount() - 1
        if is_caller:
            self.dag.vs[index]['type'] = NodeType.caller.value
        else:
            self.dag.vs[index]['type'] = NodeType.callee.value
        self.dag.vs[index]['expression'] = expression
        self.dag.vs[index]['name'] = gatename
        self.dag.vs[index]['qubits'] = qubits
        
        if len(params) > 0:
            self.dag.vs[index]['params'] = params
            self.dag.vs[index]['pindex'] = param_idx

        for i in qubits:
            leaf = self.leaves[f'_q{i}']
            self.edges.append((leaf, index))
            self.edge_attributes[len(self.edges)-1] = {"qubit": i}
            self.leaves[f'_q{i}'] = index


        if len(clbits) > 0:
            for j in clbits:
                leaf = self.leaves[f'_c{j}']
                self.edges.append((leaf, index))
                self.edge_attributes[len(self.edges)-1] = {"clbit": j}
                self.leaves[f'_c{j}'] = index

        return index

    def add_caller_node(self, gatename: str, params: List[float], qubits: List[int], clbits: List[int] = []) -> int:
        '''
        A caller node may also be one callee node for another caller node, in which case, the node is added by add_callee_node.
        '''
        self.dag.add_vertices(1)
        index = self.dag.vcount() - 1
        self.dag.vs[index]['type'] = NodeType.caller.value
        self.dag.vs[index]['name'] = gatename
        self.dag.vs[index]['qubits'] = qubits

        if len(params) > 0:
            self.dag.vs[index]['params'] = params
        # if len(param_idx) > 0:
        #     self.dag.vs[index]['pindex'] = param_idx

        for i in qubits:
            leaf = self.leaves[f'q{i}']
            self.edges.append((leaf, index))
            self.edge_attributes[len(self.edges)-1] = {"qubit": i}
            self.leaves[f'q{i}'] = index

        for j in clbits:
            leaf = self.leaves[f'c{j}']
            self.edges.append((leaf, index))
            self.edge_attributes[len(self.edges)-1] = {"clbit": j}
            self.leaves[f'c{j}'] = index

        return index

    def add_caller_matrix(self, node_index: int, matrix: np.ndarray, control_bits: int = 0, inverse: bool = False):
        self.dag.vs[node_index]['matrix'] = matrix
        self.dag.vs[node_index]['ctrl_num'] = control_bits
        self.dag.vs[node_index]['inverse'] = inverse

    def add_unitary_node(self, gatename: str, matrix: np.ndarray, qubits: List[int], ctrl_num: int, inverse: bool) -> int:
        self.dag.add_vertices(1)
        index = self.dag.vcount() - 1
        self.dag.vs[index]['type'] = NodeType.unitary.value
        self.dag.vs[index]['name'] = gatename
        self.dag.vs[index]['qubits'] = qubits
        self.dag.vs[index]['ctrl_num'] = ctrl_num
        self.dag.vs[index]['inverse'] = inverse
        self.dag.vs[index]['matrix'] = matrix
        for i in qubits:
            leaf = self.leaves[f'q{i}']
            self.edges.append((leaf, index))
            self.edge_attributes[len(self.edges)-1] = {"qubit": i}
            self.leaves[f'q{i}'] = index
        return index 

    def add_node_condition(self, node: int, clbits: List, cmp: str, val: int):
        '''
        Only use this function when creating the IR dag.
        Otherwise, the vertices in leaves may change.
        '''
        for i in clbits:
            leaf = self.leaves[f'c{i}']
            self.edges.append((leaf, node))
            self.edge_attributes[len(self.edges)-1] = {"conbit": i}
            self.leaves[f'c{i}'] = node
        self.dag.vs[node]['cmp'] = self.get_comparator(cmp)
        self.dag.vs[node]['constant'] = val

    def insert_nodes(self, instructions: List, positions: List, type: int):
        """
        Insert instructions into positions specified by gate ids.
        """
        local_leaves = {}
        path_ends = {}
        for inst, physical_qubits in instructions:
            self.dag.add_vertices(1)
            index = self.dag.vcount() - 1
            self.dag.vs[index]['type'] = type
            self.dag.vs[index]['name'] = inst.get_op()
            self.dag.vs[index]['qubits'] = physical_qubits
            if len(inst.params) > 0:
                self.dag.vs[index]['params'] = inst.params
            
            remaining_qubits = set()
            for qubit in inst.qubits:
                if qubit in local_leaves:
                    self.dag.add_edge(local_leaves[qubit], index)
                    local_leaves[qubit] = index
                else:
                    remaining_qubits.add(qubit)
            if len(remaining_qubits) > 0:
                edges_to_remove = []
                for node in positions:
                    in_edges = self.dag.vs[node].in_edges()
                    for edge in in_edges:
                        if edge['qubit'] in remaining_qubits:
                            self.dag.add_edge(edge.source, index)
                            local_leaves[edge['qubit']] = index
                            path_ends[edge['qubit']] = node
                            remaining_qubits.remove(edge['qubit'])
                            edges_to_remove.append(edge)
                    if len(remaining_qubits) == 0:
                       break        
                self.dag.delete_edges(edges_to_remove)
            if len(remaining_qubits) > 0:
                for i in remaining_qubits:
                    leaf = self.leaves[f'q{i}']
                    self.dag.add_edge(leaf, index)
        for q in path_ends.keys():
            self.dag.add_edge(local_leaves[q], path_ends[q])
    
    def substitute_nodes(self, nodes: List[int], ins_list: List[Instruction], type: int) -> List:
        """
        Substitute only 1q or 2q paths. The in_map and out_map have the same size.
        This function does not remove nodes directly because igraph will change vids after deletion.
        """
        node_set = set(nodes)
        in_map = {}
        in_conbit_map = {}
        in_edges = []
        for vindex in nodes:
            in_edges.extend(self.dag.vs[vindex].in_edges())
        in_edges.sort(key = lambda k: k.index)    
        for e in in_edges:
            if 'qubit' in e.attributes() and e['qubit'] is not None and e.source not in node_set:
                in_map[e['qubit']] = e.source
            if 'conbit' in e.attributes() and e['conbit'] is not None and e.source not in node_set:
                in_conbit_map[e['conbit']] = e.source

        out_map = {}
        out_conbit_map = {}
        out_list = []
        out_edges = []
        for vindex in nodes[::-1]:
            out_edges.extend(self.dag.vs[vindex].out_edges())
        out_edges.sort(key = lambda k: k.index)
        for e in out_edges:
            if 'qubit' in e.attributes() and e['qubit'] is not None and e.target not in node_set:
                q = e['qubit']
                out_map[q] = e.target
                out_list.append(q)
            if 'conbit' in e.attributes() and e['conbit'] is not None and e.target not in node_set:
                out_conbit_map[e['conbit']] = e.target

        new_nodes = []
        for inst in ins_list:
            self.dag.add_vertices(1)
            index = self.dag.vcount() - 1
            self.dag.vs[index]['type'] = type
            self.dag.vs[index]['name'] = inst.get_op()
            self.dag.vs[index]['qubits'] = inst.qubits
            if len(inst.params) > 0:
                self.dag.vs[index]['params'] = inst.params
            new_nodes.append(index)

            for i in inst.qubits:
                leaf = in_map[i]
                edge = self.dag.add_edge(leaf, index)
                edge["qubit"] = i
                in_map[i] = index

        for out_qubit in out_list:
            leaf = in_map[out_qubit]
            edge = self.dag.add_edge(leaf, out_map[out_qubit])
            edge["qubit"] = out_qubit

        if self.has_same_condition(nodes):
            conbits = self.get_conbits(nodes[0])
            cmp = self.dag.vs[nodes[0]]['cmp']
            const = self.dag.vs[nodes[0]]['constant']
            for n in new_nodes:
                self.dag.vs[n]['cmp'] = cmp
                self.dag.vs[n]['constant'] = const
                for clbit in conbits:
                    leaf = in_conbit_map[clbit]
                    edge = self.dag.add_edge(leaf, n)
                    edge['conbit'] = clbit
                    in_conbit_map[clbit] = n
            for out_conbit in out_conbit_map.keys():
                leaf = in_conbit_map[out_conbit]
                edge = self.dag.add_edge(leaf, out_conbit_map[out_conbit])
                edge['conbit'] = out_conbit

        return new_nodes

    def get_conbits(self, node) -> List[int]:
        """
        The condition bit array is a single clbit or a register with an ascending order.
        """
        in_edges = self.dag.vs[node].in_edges()
        conbits = []
        for e in in_edges:
            if 'conbit' in e.attributes() and e['conbit'] is not None:
                conbits.append(e['conbit'])
        conbits.sort()
        return conbits

    def has_same_condition(self, nodes: List[int]) -> bool:
        """
        Return: only return True when all the nodes has the same condition
        """
        first_node = self.dag.vs[nodes[0]]
        has_condition = 'cmp' in first_node.attributes() and first_node['cmp'] is not None
        conbits = self.get_conbits(nodes[0]) if has_condition else []
        if len(nodes) == 1:
            return has_condition
        
        if not has_condition:
            return False

        conbits = self.get_conbits(nodes[0]) if has_condition else []
        for n in nodes[1:]:
            node = self.dag.vs[n]
            n_has_condition = 'cmp' in node.attributes() and node['cmp'] is not None
            if n_has_condition != has_condition:
                return False
            if n_has_condition:
                if node['cmp'] != first_node['cmp']:
                    return False
                if node['constant'] != first_node['constant']:
                    return False
                n_conbits = self.get_conbits(n)
                if n_conbits != conbits:
                    return False
        return True

    def remove_nodes(self, nodes: List[int], keep_edge: bool =False):
        if nodes is None or len(nodes) == 0:
            return
        if keep_edge:
            in_map = {}
            for vindex in nodes:
                in_edges = self.dag.vs[vindex].in_edges()
                for e in in_edges:
                    if 'qubit' in e.attributes() and not e['qubit'] in in_map:
                        in_map[e['qubit']] = e.source

            out_map = {}
            out_list = []
            out_edges = []
            for vindex in nodes[::-1]:
                out_edges.extend(self.dag.vs[vindex].out_edges())
            out_edges.sort(key = lambda k: k.index)
            for e in out_edges:
                if 'qubit' in e.attributes() and not e['qubit'] in out_map:
                        q = e['qubit']
                        out_map[q] = e.target
                        out_list.append(q)

            for out_qubit in out_list:
                leaf = in_map[out_qubit]
                edge = self.dag.add_edge(leaf, out_map[out_qubit])
                edge["qubit"] = out_qubit

        self.dag.delete_vertices(nodes)

    def build_dag(self):
        """
        Add all the edges to the graph in one batch.
        Adding edges one by one in igraph is very slow.
        """
        self.dag["qnum"] = self.qnum
        self.dag["cnum"] = self.cnum
        self.dag.add_edges(self.edges)
        for eid, attr in self.edge_attributes.items():
            for k, v in attr.items():
                self.dag.es[eid][k] = v
    
    def plot_dag(self, layout_name="tree", save_path=None, **kargs):
        g = self.dag
        for v in g.vs:
            v["label"] = v["name"] #+ '_' + str(v.index)
        for e in g.es:
            if e['qubit'] is not None:
                e["label"] = 'q'+str(e["qubit"])
        layout = g.layout(layout_name)
        plot(g, save_path, layout=layout, **kargs)

    def get_clbits(self, node) -> List[int]:
        in_edges = self.dag.vs[node].in_edges()
        conbits = []
        for e in in_edges:
            if 'clbit' in e.attributes() and e['clbit'] is not None:
                conbits.append(e['clbit'])
        conbits.sort()
        return conbits