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
from igraph import Graph
from spinqit.compiler import IntermediateRepresentation, NodeType
from spinqit.compiler.translator.gate_converter import decompose_single_qubit_gate, decompose_multi_qubit_gate

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
    if idx == ir.dag.vcount():
        ir.insert_nodes([(inst, inst.qubits) for inst in ilist], [idx], 0)
    else:

        ir.substitute_nodes([idx], ilist, 0)
        ir.remove_nodes([idx])
