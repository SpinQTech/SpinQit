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

from spinqit.compiler.ir import NodeType, Comparator
from spinqit import SWAP, CCX, U, CP
from math import pi
import random
from copy import deepcopy

"""
Tag parsing functions
"""

def parse_comparator(comp: Comparator):
    if comp == Comparator.EQ.value:
        return '=='
    elif comp == Comparator.NE.value:
        return '!='
    elif comp == Comparator.LT.value:
        return '<'
    elif comp == Comparator.GT.value:
        return '>'
    elif comp == Comparator.LE.value:
        return '<='
    elif comp == Comparator.GE.value:
        return '>='
    else:
        raise ValueError("Unknown comparator " + comp)

def _gcd(m, n):
    return m if n == 0 else _gcd(n, m % n)

def format_params(val):
    if val == 0: return '0'
    base = 360 # divider base works for 0-9 except 7
    times = round(val/(pi/base), 5) # need round or get some 59.99999...
    if times % 1 == 0:
        sign = '' if times > 0 else '-'
        # change to fraction
        times = abs(int(times))
        common = _gcd(times, base)
        numerator = times//common
        denominator = base//common
        res = 'pi'
        if numerator != 1:
            res = str(numerator) + '*' + res
        if denominator != 1:
            res = res + '/' + str(denominator)
        res = sign + res
        return res
    else:
        return str(round(val,3))

"""
Map ir to layers functions
"""

# arrange an operation on a circuitboard to find out its layer
# @params: [circuitboard] - current circuitboard before put this gate on
# @params: [type] - gate type
# @params: [name] - gate name
# @params: [qubits] - gate qubits
# @return: the time slot, equivalent to layer idx of this gate (start from 0)
def _put_on_board(circuitboard, node) -> int:
    # use a suffix to debug different gates
    suffix = ''.join(random.sample("abcdefghijklmnopqrstuvwxyz1234567890", 4))
    largest_slot = 0
    occupy_qubits = node['qubits']
    if node['name'] in ["CX", "CY", "CZ", "CCX", "CP", "SWAP"] or type == NodeType.caller.value:  
        # all control gates, not limited to these native ones
        # need more handle for customized gate
        max_qubit = max(occupy_qubits)
        min_qubit = min(occupy_qubits)
        occupy_qubits = [i for i in range(min_qubit, max_qubit+1)]
    elif node['name'] == 'MEASURE' and ('in_clbits' in node and len(node["in_clbits"]) > 0):
        occupy_qubits = [i for i in range(occupy_qubits[0], len(circuitboard))]
    if 'in_conbits' in node and len(node["in_conbits"]) > 0:
        extra = [i for i in range(max(occupy_qubits)+1,  len(circuitboard))]
        occupy_qubits = occupy_qubits + extra
    # calc the current largest slot of all bits this gate need
    largest_slot = max(map(lambda x: len(circuitboard[x]), occupy_qubits))
    # append operation to each qubits
    time_slot = 0
    for q in occupy_qubits:
        while len(circuitboard[q]) < largest_slot:
            circuitboard[q].append('*')
        mark = node['name'] + "_" + suffix
        if node['name'] in ["CX", "CY", "CZ", "CP", "SWAP"]: 
            if q == node['qubits'][0]:
                mark = mark + "_c"
            elif q == node['qubits'][1]:
                mark = mark + "_t"
            elif q <= max(node['qubits']):
                mark = mark + "_|"
            else:
                mark = mark + "_:"
        elif node['name'] in ["CCX"]: 
            if q == node['qubits'][0] or q == node['qubits'][1]:
                mark = mark + "_c"
            elif q == node['qubits'][2]:
                mark = mark + "_t"
            elif q <= max(node['qubits']):
                mark = mark + "_|"
            else:
                mark = mark + "_:"
        else:
            if q not in node['qubits']:
                mark = mark + "_:"
        circuitboard[q].append(mark)
        time_slot = max(time_slot, len(circuitboard[q]))
    return largest_slot

# convert a graph vertex to a circuit view layer node
# @params: [v] - an igraph vertex in ir
# @return: [node] - a layer node used in draw
def _vertex_to_node(v):
    node = deepcopy(v.attributes())
    # current all local commands are base gates
    if node["type"] == NodeType.callee.value:
        node["type"] = NodeType.op.value 
    # filter gate name
    if node["type"] == NodeType.op.value:
        if node["name"] == SWAP.label:
            node["name"] = "SWAP"
        elif node["name"] == CP.label:
            node["name"] = "CP"
        elif node["name"] == CCX.label:
            node["name"] = "CCX"
        elif node["name"] == U.label:
            node["name"] = "U"
    # add input clbits and conbits in it for measure and cif
    in_clbits = []
    in_conbits = []
    for e in v.in_edges():
        attrs = e.attributes()
        if 'clbit' in attrs and attrs['clbit'] is not None and attrs['clbit'] not in in_clbits:
            in_clbits.append(attrs['clbit'])
        if 'conbit' in attrs and attrs['conbit'] is not None and attrs['conbit'] not in in_clbits:
            in_conbits.append(attrs['conbit'])
    if len(in_clbits) > 0:
        node["in_clbits"] = in_clbits
    if len(in_conbits) > 0:
        node["in_conbits"] = in_conbits
    return node

# extend a customized gate to a list of operations by its definition
# final global params and qubits of these operations are calculated based on real params get by the caller of this customized gate
# @params: [ir] - circuit ir, used to find operations in gate definition
# @params: [caller] - caller node of this customized gate definition
# @params: [sorted_vidx_list] - graph vertex indexes after topological sorting, used to sort customized gate operations
# @return: [vnode_list] - a list of circuit layer nodes in called order (sorted by bfs)
def _extend_customized_gate(ir, caller, sorted_vidx_list):
    def_v = ir.dag.vs.find(caller['name'], type=2)
    vidx_list, _, _ = ir.dag.bfs(def_v.index)
    vidx_list = vidx_list[1:] # remove definition itself
    vidx_list = [vidx for vidx in sorted_vidx_list if vidx in vidx_list]
    vnode_list = []
    for vidx in vidx_list: 
        node = _vertex_to_node(ir.dag.vs[vidx])
        # map quibits
        final_qubits = []
        for x in node["qubits"]:
            if x >= len(caller["qubits"]):
                raise ValueError("Global qubits with idx = " + str(x) + " does not exists.")
            else:
                final_qubits.append(caller["qubits"][x])
        node["qubits"] = final_qubits
        # calc params
        # pindex是所有local参数按序排列，不和params一一对应，params按顺序读取需要数量的参数        
        if node['params'] is not None and len(node['params']) > 0:
            final_args = []
            start = 0
            for p in node['params']:
                if isinstance(p, (int, float)):
                    final_args.append(p)
                else:
                    if len(node['pindex']) == 1 and node['pindex'][0] == -1:
                        final_args.append(p(caller["params"]))
                    else:
                        local_args = []
                        arg_count = p.__code__.co_argcount
                        local_args = [] if arg_count == 0 else node['pindex'][start:start + arg_count]
                        start += arg_count
                        arg_inputs = []
                        for x in local_args:
                            if x >= len(caller["params"]):
                                raise ValueError("Global args with idx = " + str(x) + " does not exists.")
                            else:
                                arg_inputs.append(caller["params"][x])
                        func_arg = p(*arg_inputs)
                        final_args.append(func_arg)
                    # node['pindex'] = None
            node['params'] = final_args
        # add ctrl and cond bits for measure and cif
        if 'cmp' in caller:
            node["cmp"] = caller["cmp"]
        if 'constant' in caller:
            node["constant"] = caller["constant"]
        if 'in_clbits' in caller:
            node["in_clbits"] = caller["in_clbits"]
        if 'in_conbits' in caller:
            node["in_conbits"] = caller["in_conbits"]
        vnode_list.append(node)
    return vnode_list

# put operations on a circuitboard to get its view layer index
# decompose customized gate recursively according to the feature view_decompose_level. If cur_decompose_level < view_decompose_level, 
# decompose the customized gate to a list of operations, and then put the operations into the circuitboard. Otherwise, directly put 
# the current gate into the circuitboard.
# circuitboard and graph_node_list will be filled during the function
# @params: [ir] - circuit ir, used to find operations in customized gate definition
# @params: [sorted_vidx_list] - graph vertex indexes after topological sorting, used to sort customized gate operations
# @params: [vnode_list] - a list of circuit layer nodes in called order (sort by topology), prepared to be put into the circuitboard
# @params: [vnode_list] - a list of circuit layer nodes have been put into circuitboard and have their timeSlot been calculated
# @params: [circuitboard] - a two-dimension array used to simulate the position of gates in a view
# @params: [view_decompose_level] - desired decompose level of the final view
# @params: [cur_decompose_level] - current decompose level of nodes in vnode_list
def _recursive_put_on_board(ir, sorted_vidx_list, vnode_list, graph_node_list, circuitboard, view_decompose_level, cur_decompose_level=0):
    for node in vnode_list:
        if node["type"] == NodeType.op.value or (node["type"] == NodeType.caller.value and cur_decompose_level >= view_decompose_level):
            node["timeSlot"] = _put_on_board(circuitboard, node)
            graph_node_list.append(node)
        elif node["type"] == NodeType.caller.value and cur_decompose_level < view_decompose_level:
            callee_list = _extend_customized_gate(ir, node, sorted_vidx_list)
            _recursive_put_on_board(ir, sorted_vidx_list, callee_list, graph_node_list, circuitboard, view_decompose_level, cur_decompose_level+1)

# convert an ir dag to a list of view layers
# each layer contains the operations occur at the same time slot
# when view_decompose_level = n > 0, customized gates in the circuit will be decomposed to a list of operation recursively for n times
# @params: [ir] - circuit ir
# @params: [view_decompose_level] - desired decompose level of the final view
# @return: [qubit_size] - number of qubits registed by this circuit
# @return: [clbit_size] - number of qubits registed by this circuit
# @return: [max_slot] - max timeslots of this circuit, equivalent to the number of layers
# @return: [layers] - view layers, represent lists of operations occurs at each timeslot
def dag_to_layers(ir, view_decompose_level):
    # all gate vertex sorted by topology
    vidx_list = ir.dag.topological_sorting() # use g.vs[vidx] to get each vertex

    # filter out definitions, only track main thread
    delete_list = []
    for vidx in vidx_list:
        vs = ir.dag.vs[vidx]
        if vs.indegree() == 0 and vs['type'] != NodeType.register.value:
            sub_vidx_list = ir.dag.subcomponent(vs)
            delete_list.extend(sub_vidx_list)
    main_thread_vidx_list = list(filter(lambda x: x not in delete_list, vidx_list))

    # get total qubit_size, total clbit_size, and view nodes
    qubit_size = 0
    clbit_size = 0
    vnode_list = []
    for vidx in main_thread_vidx_list:
        vs = ir.dag.vs[vidx]
        # calc bits
        if vs["type"] == NodeType.init_qubit.value:
            qubit_size = qubit_size + 1
        elif vs["type"] == NodeType.init_clbit.value:
            clbit_size = clbit_size + 1
        if vs["type"] == NodeType.op.value or vs["type"] == NodeType.caller.value:
            node = _vertex_to_node(vs)
            vnode_list.append(node)

    # fill board according to vs_list
    circuitboard = [[] for i in range(qubit_size)]
    graph_node_list = []
    _recursive_put_on_board(ir, vidx_list, vnode_list, graph_node_list, circuitboard, view_decompose_level, cur_decompose_level=0)
    
    # convert board to layers
    max_slot = max(map(lambda x: len(x), circuitboard))
    layers = [[] for i in range(max_slot)]
    for node in graph_node_list:
        layers[node["timeSlot"]].append(node)
    
    return (qubit_size, clbit_size, max_slot, layers)
