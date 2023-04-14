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

from typing import List, Dict, Set
from igraph import Graph
from spinqit.compiler.ir import NodeType, IntermediateRepresentation
from ..exceptions import CircuitOperationParsingError, CircuitOperationValidationError
from .gate import *
from .platform import *
from typing import Optional
from ..gates import H, CX, CY, CZ, CCX
from ..instruction import Instruction
import math
from queue import Queue

class CircuitOperation:
    def __init__(self, time_slot: int, gate: Gate, nativeOperation: bool = True, qubits: List = [], arguments: List = []):
        self._time_slot = time_slot
        self._gate = gate
        self._nativeOperation = nativeOperation
        self._qubits = qubits
        self._arguments = arguments

    @property
    def time_slot(self) -> int:
        return self._time_slot

    @property
    def gate(self) -> Gate:
        return self._gate

    @property
    def nativeOperation(self) -> Gate:
        return self._nativeOperation

    @property
    def arguments(self):
        return self._arguments

    @property
    def qubits(self):
        return self._qubits

    def to_dict(self):
        co_dict = {"timeSlot": self._time_slot, "nativeOperation": self._nativeOperation, "gate": self._gate.to_dict(), "qubits": self._qubits, "arguments": self._arguments}
        return co_dict

class Circuit:
    def __init__(self, operations: List[CircuitOperation] = [], definitions: List = []):
        self._operations = operations
        self._definitions = definitions
    
    @property
    def operations(self):
        return self._operations

    @property
    def definitions(self):
        return self._definitions

    def to_dict(self):
        return {"operations": [o.to_dict() for o in self._operations], "definitions": []}

def _count_qubits(vs):
        count = 0
        for v in vs:
            if v["type"] == NodeType.init_qubit.value:
                count = count + 1
        return count

def convert_cz(v):
    edges = v.in_edges()
    edges.sort(key = lambda k : k.index)
    qubits = []
    clbits = []
    for e in edges:
        if 'qubit' in e.attributes():
            qubits.append(e['qubit'])
        elif 'clbit' in e.attributes():
            clbits.append(e['clbit'])
    subgates = []
    subgates.append(Instruction(H, [qubits[1]], clbits))
    subgates.append(Instruction(CX, qubits, clbits))
    subgates.append(Instruction(H, [qubits[1]], clbits))
    return subgates

def _add_swaps_to_circuit(circuitboard, swap_qubits) -> List[CircuitOperation]:
    op_list = []
    for qubits in swap_qubits:
        op_list.append(_vertex_to_circuit_operation(circuitboard, 'CNOT', qubits, []))
        op_list.append(_vertex_to_circuit_operation(circuitboard, 'CNOT', qubits[::-1], []))
        op_list.append(_vertex_to_circuit_operation(circuitboard, 'CNOT', qubits, []))
    return op_list

def _vertex_to_circuit_operation(circuitboard, name, qubits, arguments) -> CircuitOperation:
    if name == CX.label:
        name = 'CNOT'
    elif name == CY.label:
        name = 'YCON'
    elif name == CZ.label:
        name = 'ZCON'
    elif name == CCX.label:
        name = 'CCNOT'
    gate = find_gate(name)
    if gate is None:
        raise CircuitOperationParsingError("Gate with name = " + name + " is not support by spinq cloud.")
    largest_slot = 0
    if gate.gtag == 'Barrier':
        qubits = [q+1 for q in qubits]
        # calc the time_slot of the barrier gate
        for q in qubits:
            largest_slot = max(largest_slot, len(circuitboard[q]))
        # append operation to each qubits
        for q in qubits:
            while len(circuitboard[q]) < largest_slot:
                circuitboard[q].append('*')
            circuitboard[q].append(gate.gname)
        # convert to our operation structure
        return  CircuitOperation(largest_slot+1, gate, True, qubits, arguments)
    elif gate.gtag == "C2":  # two-bits gates
        qubits = [qubits[1]+1, qubits[0]+1]
        # get the largest slot involved in this gate, including the qubits between the controller and target
        for row in circuitboard[min(qubits)-1:max(qubits)]:
            largest_slot = max(largest_slot, len(row))
        # append operation to each qubits
        for row_idx in range(min(qubits)-1, max(qubits)):
            row = circuitboard[row_idx]
            while len(row) < largest_slot:
                row.append('*')
            if row_idx == (qubits[1]-1):
                row.append(gate.gname + "_c")
            elif row_idx == (qubits[0]-1):
                row.append(gate.gname + "_t")
            else:
                row.append('|')
        return  CircuitOperation(largest_slot+1, gate, True, qubits, arguments)
    elif gate.gtag == "C3": # two-control gates
        qubits = [qubits[2]+1, qubits[0]+1, qubits[1]+1]
        for row in circuitboard[min(qubits)-1:max(qubits)]:
            largest_slot = max(largest_slot, len(row))
        # append operation to each qubits
        for row_idx in range(min(qubits)-1, max(qubits)):
            row = circuitboard[row_idx]
            while len(row) < largest_slot:
                row.append('*')
            if row_idx == (qubits[1]-1):
                row.append(gate.gname + "_c")
            elif row_idx == (qubits[2]-1):
                row.append(gate.gname + "_c")
            elif row_idx == (qubits[0]-1):
                row.append(gate.gname + "_t")
            else:
                row.append('|')
        return  CircuitOperation(largest_slot+1, gate, True, qubits, arguments)
    elif gate.gtag == "U1":
        # U(theta, phi, lambda) to Rz(phi)Ry(theta)Rz(lambda)
        circuitboard[qubits[0]].append(gate.gname)
        # convert to our operation structure
        theta = round (float(math.degrees(arguments[0])), 1)
        phi = round (float(math.degrees(arguments[1])), 1)
        lam = round (float(math.degrees(arguments[2])), 1)
        qubits = [qubits[0]+1]
        arguments = [theta, phi, lam]
        return  CircuitOperation(len(circuitboard[qubits[0]-1]), gate, True, qubits, arguments)
    elif gate.gtag == "R1":
        # convert to our operation structure
        degree = round (float(math.degrees(arguments[0]))%720, 1)
        circuitboard[qubits[0]].append(gate.gname + " " + str(degree))
        qubits = [qubits[0]+1]
        arguments = [degree]
        return  CircuitOperation(len(circuitboard[qubits[0]-1]), gate, True, qubits, arguments)
    elif gate.gtag in ['C1', 'Measure']:
        circuitboard[qubits[0]].append(gate.gname)
        qubits = [qubits[0]+1]
        return CircuitOperation(len(circuitboard[qubits[0]-1]), gate, True, qubits, arguments)
    else:
        raise CircuitOperationParsingError("Gate with tag = " + gate.gtag + " is not support by spinq cloud.")

# customized operation dictionary
customized_op = {}

def _transfer_qubits(global_qlist, local_qlist):
    return [global_qlist[x] for x in local_qlist]

def _transfer_arguments(global_arguments, local_arguments, func):
    args = [global_arguments[x] for x in local_arguments]
    return func(*args)

def _dfs(root_index: int, graph: Graph, visited: Set, result: List):
    successors = graph.neighbors(root_index, mode='out')
    for s in successors:
        if not s in visited:
            _dfs(s, graph, visited, result)
    result.append(root_index)
    visited.add(root_index)

def topological_sort_by_dfs(roots: List[int], graph: Graph):
    visited = set()
    result = []
    for vidx in roots:
        _dfs(vidx, graph, visited, result)
    return result[::-1]

def _expand_customized_gate(def_name: str, g: Graph):
    def_v = g.vs.find(def_name, type=NodeType.definition.value)
    callee_idx_list = topological_sort_by_dfs([def_v.index], g)
    callee_idx_list = callee_idx_list[1:]
    sorted_callee_list = [g.vs[idx] for idx in callee_idx_list ]
    return sorted_callee_list

def _customized_vertex_to_circuit_operation(circuitboard, gatename, vindex, global_qubits, global_arguments, 
                                            swap_fixes, gate_updates, graph) -> List[CircuitOperation]:    

    callee_list = customized_op[gatename]
    oplist = []
    for callee in callee_list:
        sub_qubits = callee['qubits']
        final_qubits = _transfer_qubits(global_qubits, sub_qubits)
        final_arguments = []
        if callee['params'] is not None and len(callee['params']) > 0:
            start = 0
            for p in callee['params']:
                if isinstance(p, (int, float)):
                    final_arguments.append(p)
                else:
                    if len(callee['pindex']) == 1 and callee['pindex'][0] == -1:
                        final_arg = p(global_arguments)
                    else:
                        local_args = []
                        arg_count = p.__code__.co_argcount
                        local_args = [] if arg_count == 0 else callee['pindex'][start:start + arg_count]
                        start += arg_count
                        arg_inputs = []
                    
                        for x in local_args:
                            if x >= len(global_arguments):
                                raise ValueError("Global args with idx = " + str(x) + " does not exists.")
                            else:
                                arg_inputs.append(global_arguments[x])
                        final_arg = p(*arg_inputs)
                    final_arguments.append(final_arg)
        if isinstance(vindex, tuple):
            gate_index = (*vindex, callee.index)
        else:
            gate_index = (vindex, callee.index)
        
        if swap_fixes is not None and gate_index in swap_fixes:
            swap_list = _add_swaps_to_circuit(circuitboard, swap_fixes[gate_index])
            oplist.extend(swap_list)
        if gate_updates is not None and gate_index in gate_updates:
            final_qubits = gate_updates[gate_index]

        if callee["type"] == NodeType.caller.value:
            callername = callee["name"]
            if callername not in customized_op:
                customized_op[callername] = _expand_customized_gate(callername, graph)
            result_list = _customized_vertex_to_circuit_operation(circuitboard, callername, gate_index, final_qubits, final_arguments, swap_fixes, gate_updates, graph)
            oplist.extend(result_list)
        else:
            op = _vertex_to_circuit_operation(circuitboard, callee["name"], final_qubits, final_arguments)
            oplist.append(op)
    return oplist

def _is_valid(operation: CircuitOperation, platform: Platform) -> bool:
    if not platform.has_gate(operation.gate):
        raise CircuitOperationValidationError("Current platform does not support " + operation.gate.gname + " gate.")
    return True

def graph_to_circuit(ir: IntermediateRepresentation, 
                    logical_to_physical: Dict, 
                    platform:Optional[Platform]=None, 
                    swap_fixes: Optional[List]=None, 
                    gate_updates:Optional[List]=None) -> Circuit:
    global customized_op

    registers = ir.dag.vs.select(type = NodeType.register.value)
    reg_indices = [node.index for node in registers]
    main_thread_vidx_list = topological_sort_by_dfs(reg_indices, ir.dag)
    main_thread_vx_list = [ir.dag.vs[vidx] for vidx in main_thread_vidx_list]

    # get total qubit_size
    qubit_size = _count_qubits(main_thread_vx_list)
    if platform is not None and platform.max_bitnum < qubit_size:
        raise CircuitOperationValidationError("Register more bits than the platform supplies.")
    # convert each vertex in graph to a circuit operation
    # only go through main thread

    operations = []
    circuitboard = [[] for i in range(qubit_size)]
    for v in main_thread_vx_list:
        if v["type"] == NodeType.op.value:
            arguments = []
            if 'params' in v.attributes() and v['params'] is not None and len(v['params']) > 0:
                arguments = v['params']
            # single gate
            if swap_fixes is not None and v.index in swap_fixes:
                swap_list = _add_swaps_to_circuit(circuitboard, swap_fixes[v.index])
                operations.extend(swap_list)
            if gate_updates is not None and v.index in gate_updates:
                physical_qubits = gate_updates[v.index]
            else:
                physical_qubits = [logical_to_physical[q] for q in v['qubits']]      
            op = _vertex_to_circuit_operation(circuitboard, v['name'], physical_qubits, arguments)
            if platform is None or _is_valid(op, platform):
                operations.append(op)
        elif v["type"] == NodeType.caller.value:
            # customized gate
            gatename = v["name"]
            if gatename not in customized_op:
                customized_op[gatename] = _expand_customized_gate(gatename, ir.dag)
            
            global_qubits = [logical_to_physical[q] for q in v['qubits']]
            global_arguments = v['params']
            oplist = _customized_vertex_to_circuit_operation(circuitboard, gatename, v.index, global_qubits, global_arguments, swap_fixes, gate_updates, ir.dag)

            if platform is not None:
                for op in oplist:
                    if _is_valid(op, platform):
                        operations.append(op)
            else:
                operations.extend(oplist)
    # reset customized_op
    customized_op = {}            
    return Circuit(operations=operations)

