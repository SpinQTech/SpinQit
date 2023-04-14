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

from math import pi
from igraph import Graph
from .backend_util import get_graph_capsule
from spinqit.compiler import IntermediateRepresentation, NodeType
from spinqit.model import Instruction
from spinqit.model import I, H, X, Y, Z, Rx, Ry, Rz, T, Td, S, Sd, P, CX, CY, CZ, SWAP, CCX, U, MEASURE
from spinqit.spinq_backends import NMR

class NMRConfig:
    def __init__(self):
        self.metadata = {}

    def configure_shots(self, shots: int):
        self.metadata['shots'] = shots

    def configure_ip(self, addr: str):
        self.metadata['ip'] = addr

    def configure_port(self, port: int):
        self.metadata['port'] = port

    def configure_account(self, username: str, password: str):
        self.metadata['username'] = username
        self.metadata['password'] = password

    def configure_task(self, task_name: str, task_desc: str):
        self.metadata['task_name'] = task_name
        self.metadata['task_desc'] = task_desc

    def configure_print_circuit(self, verbose: bool = True):
        self.metadata['print_circuit'] = verbose

class NMRBackend:
    def __init__(self):
        self.machine = NMR()

    def assemble(self, ir: IntermediateRepresentation):
        if 'qnum' not in ir.dag.attributes() or ir.dag['qnum'] <= 0 or ir.dag['qnum'] > 3:
            raise Exception('NMR only supports a circuit with 0 to 3 qubits.')
        i = 0
        while i < ir.dag.vcount():
            v = ir.dag.vs[i]
            if v['type'] == NodeType.op.value or v['type'] == NodeType.callee.value:
                if 'cmp' in v.attributes() and v['cmp'] is not None:
                    raise Exception('NMR does not support conditional gates.')
                if v['name'] == MEASURE.label:
                    raise Exception('NMR does not support the MEASURE gate.')
                if v['name'] == SWAP.label:
                    edges = v.in_edges()
                    edges.sort(key = lambda k: k.index)
                    qubits = []
                    clbits = []
                    for e in edges:
                        if 'qubit' in e.attributes() and e['qubit'] is not None:
                            qubits.append(e['qubit'])
                        elif 'clbit' in e.attributes() and e['clbit'] is not None:
                            clbits.append(e['clbit'])
                    subgates = []
                    for sg, qidx in SWAP.factors:
                        subgates.append(Instruction(sg, [qubits[i] for i in qidx], clbits))
                    ir.substitute_nodes([v.index], subgates, v['type'])
                    ir.remove_nodes([v.index], False)
                    i -= 1
                elif v['name'] == U.label:
                    edges = v.in_edges()
                    qubits = []
                    clbits = []
                    for e in edges:
                        if 'qubit' in e.attributes() and e['qubit'] is not None:
                            qubits.append(e['qubit'])
                        elif 'clbit' in e.attributes() and e['clbit'] is not None:
                            clbits.append(e['clbit'])
                    subgates = []
                    
                    if v['type'] == NodeType.op.value:
                        # for sg, qidx, pexp in U.factors:
                        #     subgates.append(Instruction(sg, [qubits[i] for i in qidx], clbits, pexp(v['params'])))
                        subgates.append(Instruction(Rz, qubits, clbits, v['params'][2]))
                        subgates.append(Instruction(Ry, qubits, clbits, v['params'][0]))
                        subgates.append(Instruction(Rz, qubits, clbits, v['params'][1]))
                        ir.substitute_nodes([v.index], subgates, v['type'])
                        ir.remove_nodes([v.index], False)
                    else:
                        pindex_group = []
                        var_full = v['pindex']
                        start = 0
                        for func in v['params']:
                            arg_count = func.__code__.co_argcount
                            var_slice = [] if arg_count == 0 else var_full[start:start + arg_count]
                            pindex_group.append(var_slice)
                            start += arg_count

                        subgates.append(Instruction(Rz, qubits, clbits, v['params'][2]))
                        subgates.append(Instruction(Ry, qubits, clbits, v['params'][0]))
                        subgates.append(Instruction(Rz, qubits, clbits, v['params'][1]))
                        new_nodes = ir.substitute_nodes([v.index], subgates, v['type'])

                        nv1 = ir.dag.vs[new_nodes[0]]
                        nv1['pindex'] = pindex_group[2]
                        nv2 = ir.dag.vs[new_nodes[1]]
                        nv2['pindex'] = pindex_group[0]
                        nv3 = ir.dag.vs[new_nodes[2]]
                        nv3['pindex'] = pindex_group[1]
                        ir.remove_nodes([v.index], False)
                    i -= 1
                elif v['name'] == P.label:
                    v['name'] = Rz.label
                elif v['name'] == Sd.label:
                    v['name'] = Rz.label
                    v['params'] = [-pi/2]
                elif v['name'] == CX.label:
                    v['name'] = 'CNOT'
                elif v['name'] == CY.label:
                    v['name'] = 'YCON'
                elif v['name'] == CZ.label:
                    v['name'] = 'ZCON'
                elif v['name'] == CCX.label:
                    v['name'] = 'CCX'
            i += 1

    def execute(self, ir: IntermediateRepresentation, config: NMRConfig):
        self.assemble(ir)
        return self.machine.execute(get_graph_capsule(ir.dag), config.metadata)