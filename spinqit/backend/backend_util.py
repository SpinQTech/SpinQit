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

from typing import List
from copy import copy
from igraph import Graph
from math import pi
from spinqit.compiler import IntermediateRepresentation, NodeType
from spinqit.compiler.translator.gate_converter import decompose_single_qubit_gate, decompose_multi_qubit_gate
from spinqit.model import H, Ry, Rz, Sd, P, CX, CY, CZ, SWAP, CCX, U, MEASURE, StateVector


def _get_qubit_terminal_nodes(ir):
    terminal_nodes = {}
    for vid in ir.dag.topological_sorting(mode='OUT'):
        v = ir.dag.vs[vid]
        if v['type'] == NodeType.init_qubit.value:
            parts = v['name'].split('_')
            if len(parts) == 3 and parts[0].startswith('q'):
                terminal_nodes[int(parts[0][1:]) + int(parts[2])] = vid
        elif v['type'] in (NodeType.op.value, NodeType.caller.value, NodeType.unitary.value):
            if 'qubits' in v.attributes() and v['qubits'] is not None:
                for qubit in v['qubits']:
                    terminal_nodes[int(qubit)] = vid
    return terminal_nodes


def _append_basis_rotation_node(ir, terminal_nodes, gate, qubit, params=None, before=None):
    if qubit not in terminal_nodes:
        raise ValueError(f'Cannot find qubit {qubit} in the circuit.')

    if before is not None:
        incoming = [e for e in ir.dag.vs[before].in_edges()
                    if e.attributes().get('qubit') == qubit]
        if len(incoming) != 1:
            raise ValueError('Measurement has no unique input for qubit {}'.format(qubit))
        terminal_nodes[qubit] = incoming[0].source
        ir.dag.delete_edges([incoming[0].index])

    ir.dag.add_vertices(1)
    node_idx = ir.dag.vcount() - 1
    v = ir.dag.vs[node_idx]
    v['type'] = NodeType.op.value
    v['name'] = gate.label
    v['qubits'] = [qubit]
    if params:
        v['params'] = params
    edge = ir.dag.add_edge(terminal_nodes[qubit], node_idx)
    edge['qubit'] = qubit
    terminal_nodes[qubit] = node_idx
    if before is not None:
        ir.dag.add_edge(node_idx, before, qubit=qubit)
    return node_idx


def _basis_rotation(pauli_string, qubits, ir):
    if len(pauli_string) != len(qubits):
        raise ValueError(
            'The Pauli string length should match the number of measured qubits.'
        )

    if any(pauli.upper() not in 'IXYZ' for pauli in pauli_string):
        raise ValueError('The input string is not a Pauli string')
    terminal_nodes = _get_qubit_terminal_nodes(ir)
    if any(int(q) not in terminal_nodes for q in qubits):
        raise ValueError('Measured qubit is not in the circuit')
    measurements = {}
    for vid in ir.dag.topological_sorting(mode='OUT'):
        vertex = ir.dag.vs[vid]
        if vertex['type'] == NodeType.op.value and vertex['name'] == 'MEASURE':
            for qubit in vertex['qubits']:
                measurements.setdefault(qubit, vid)
    node_idx_list = []
    for pauli, qubit in zip(pauli_string, qubits):
        qubit = int(qubit)
        pauli = pauli.upper()
        if pauli == 'X':
            node_idx_list.append(
                _append_basis_rotation_node(ir, terminal_nodes, H, qubit, before=measurements.get(qubit))
            )
        elif pauli == 'Y':
            node_idx_list.append(
                _append_basis_rotation_node(ir, terminal_nodes, Sd, qubit, before=measurements.get(qubit))
            )
            node_idx_list.append(
                _append_basis_rotation_node(ir, terminal_nodes, H, qubit, before=measurements.get(qubit))
            )
        elif pauli in ('I', 'Z'):
            continue
        else:
            raise ValueError('The input string is not a Pauli string')
    ir._refresh_graph_records()
    return node_idx_list



def lazy_property(fn):
    """
    A lazy property decorator.
    The function decorated is called the first time to retrieve the result and
    then that calculated result is used the next time you access the value.
    """
    attr = '_lazy__' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr):
            setattr(self, attr, fn(self))
        return getattr(self, attr)

    return _lazy_property

def get_graph_capsule(graph: Graph):
    return graph.__graph_as_capsule()

def map_results(probabilities: List, qubit_mapping: List) -> List:
    qubit_num = len(qubit_mapping)
    zero_probabilitiess = [0.0] * qubit_num
    for i in range(len(probabilities)):
        for j in range(qubit_num):
            if (i >> (qubit_num - qubit_mapping[j] - 1)) & 1 == 0:
                zero_probabilitiess[j] += probabilities[i]

    logical_probabilities = [1.0] * (2 ** qubit_num)
    for k in range(len(logical_probabilities)):
        for q in range(qubit_num):
            if ((k >> (qubit_num - q - 1)) & 1) == 0:
                logical_probabilities[k] *= zero_probabilitiess[q]
            else:
                logical_probabilities[k] *= (1.0 - zero_probabilitiess[q])

    return logical_probabilities

def analyze_connectivity(ir: IntermediateRepresentation) -> List:
    connectivity = []
    for v in ir.dag.vs:
        if v['type'] == NodeType.op.value or NodeType.caller.value:
            edges = v.in_edges()
            if len(edges) > 1:
                qubits = []
                for e in edges:
                    if 'qubit' in e.attributes() and e['qubit'] is not None:
                        qubits.append(e['qubit'])
                if len(qubits) > 1:
                    for i in range(len(qubits)):
                        for j in range(i+1, len(qubits)):
                            connectivity.append(qubits[i], qubits[j])
    return connectivity


def _check_ir_measure(ir):
    for i in range(ir.dag.vcount() - 1, -1, -1):
        if ir.dag.vs[i]['name'] == 'MEASURE':
            idx = i
            return idx
    return False

def _add_pauli_gate(gate, qubits, ir):
    if gate.qubit_num == 1:
        ilist = decompose_single_qubit_gate(gate, qubits, )
    else:
        ilist = decompose_multi_qubit_gate(gate, qubits)
    idx = _check_ir_measure(ir)
    idx = idx if idx is not False else ir.dag.vcount()
    node_idx_list = []
    if idx == ir.dag.vcount():
        seq = ir.dag.vs.select(lambda x: len(x.out_edges()) != len(x.in_edges()) and x['type'] != 4)
        node_map = {}
        for v in seq:
            if v['qubits'] is None:
                _qubits = [int(v['name'].split('_')[-1])]
            else:
                _qubits = v['qubits']
            for q in _qubits:
                node_map[q] = v.index
        for inst in ilist:
            node_idx = ir.add_op_node(inst.gate.label, inst.params, inst.qubits, inst.clbits)
            prev_node_idx = node_map[ir.dag.vs[node_idx]['qubits'][0]]
            edge = ir.dag.add_edge(prev_node_idx, node_idx, )
            # edge['qubit'] = inst.qubits
            node_idx_list.append(node_idx)
        return node_idx_list
    else:
        node_idx_list = ir.substitute_nodes([idx], ilist, 0)
        ir.remove_nodes([idx])
        return node_idx_list



def _basis_rotation_ir(pauli_string, qubits, ir):
    """Run each Pauli term on its own graph, preserving parameter gradients."""
    working = copy(ir)
    working.dag = ir.dag.copy()
    working.leaves = dict(ir.leaves)
    working.edges = list(ir.edges)
    working.edge_attributes = {i: dict(attrs) for i, attrs in ir.edge_attributes.items()}
    working.include_gate = set(ir.include_gate)
    _basis_rotation(pauli_string, qubits, working)
    return working
