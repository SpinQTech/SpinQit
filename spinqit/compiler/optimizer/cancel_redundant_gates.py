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
from math import pi
from ..ir import *
from .analyze_path import analyze, X_series, Y_series, Z_series
from spinqit.model import Instruction
from spinqit.model import X, Y, Z, T, Td, S, Sd, Rx, Ry, Rz

class CancelRedundantGates():
    def __init__(self) -> None:
        pass

    def cancel_rotation_gates(self, path: List[int], ir: IntermediateRepresentation):
        total_angle = 0
        for node in path:
            name = ir.dag.vs[node]['name']
            if name in [X.label, Y.label, Z.label]:
                total_angle += pi
            elif name == T.label:
                total_angle += pi/4
            elif name == Td.label:
                total_angle -= pi/4
            elif name == S.label:
                total_angle += pi/2
            elif name == Sd.label:
                total_angle -= pi/2
            else:
                total_angle += ir.dag.vs[node]['params'][0]
        total_angle = total_angle % (4*pi)
        edges = ir.dag.vs[path[0]].in_edges()
        qarg = edges[0]['qubit']

        ptype = ir.dag.vs[path[0]]['type']
        gname = ir.dag.vs[path[0]]['name']
        if gname in X_series:
            gate = Rx
        elif gname in Y_series:
            gate = Ry
        elif gname in Z_series:
            gate = Rz

        inst = Instruction(gate, [qarg], [], total_angle)
        ir.substitute_nodes(path, [inst], ptype)

    def cancel_same_gates(self, paths: List[List], index: int):
        if len(paths[index]) % 2 == 1:
            paths[index] = paths[index][1:]

    def run(self, ir: IntermediateRepresentation):
        path_list = analyze(ir.dag)
        keep_edge = []
        for i in range(len(path_list)):
            if len(path_list[i]) > 1:
                ptype = ir.dag.vs[path_list[i][0]]['name']
                if ptype in X_series or ptype in Y_series or ptype in Z_series:
                    self.cancel_rotation_gates(path_list[i], ir)
                    keep_edge.append(False)
                else:
                    self.cancel_same_gates(path_list, i)
                    keep_edge.append(True)
                    
        i = 0
        keep_list = []
        non_keep_list = []
        for path in path_list:
            if len(path) > 1:
                if keep_edge[i]:
                    keep_list.extend(path)
                else:
                    non_keep_list.extend(path)
                i += 1
        ir.remove_nodes(keep_list, True)
        ir.remove_nodes(non_keep_list, False)
