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

from igraph import Vertex, Graph
from ..ir import NodeType
from .util import get_qubits, get_paths
from spinqit.model import I, H, X, Y, Z, Rx, Ry, Rz, T, Td, S, Sd, P, CX, CY, CZ, SWAP, CCX

X_series = {X.label, Rx.label}
Y_series = {Y.label, Ry.label}
Z_series = {Z.label, Rz.label, T.label, Td.label, S.label, Sd.label, P.label}
CU_series = {CX.label, CY.label, CCX.label}
SWAP_Series = {CZ.label, SWAP.label}

def is_commutative(cur: Vertex, pre: Vertex):
    if cur['name'] in X_series and pre['name'] in X_series:
        return True
    elif cur['name'] in Y_series and pre['name'] in Y_series:
        return True
    elif cur['name'] in Z_series and pre['name'] in Z_series:
        return True
    elif cur['name'] == H.label and pre['name'] == H.label:
        return True
    elif cur['name'] in CU_series:
        if cur['name'] != pre['name']:
            return False
        cur_qubits = cur['qubits']
        pre_qubits = pre['qubits']
        if cur_qubits != pre_qubits:
            return False
        return True
    elif cur['name'] in SWAP_Series:
        if cur['name'] != pre['name']:
            return False
        cur_qubits = set(cur['qubits'])
        pre_qubits = set(pre['qubits'])
        if cur_qubits != pre_qubits:
            return False
        return True
    elif cur['name'] == I.label:
        return True
    else:
        return False

def cancellation_filter(v: int, g: Graph):
    if 'cmp' in g.vs[v].attributes() and g.vs[v]['cmp'] is not None:
        return False
    prev = g.predecessors(g.vs[v])
    if len(prev) == 0:
        return False
   
    cur_type = g.vs[v]['type']
    type_flag = cur_type == NodeType.op.value or cur_type == NodeType.callee.value
    prev_flag = True
    for p in prev:
        pre_type = g.vs[p]['type']
        if cur_type == pre_type:
            prev_flag = False
    if type_flag and prev_flag:
        return True

    if len(set(prev)) != 1:
        return False

    return is_commutative(g.vs[v], g.vs[prev[0]])

def analyze(g: Graph):
    """Group compatible adjacent gates, checking both ends of each step."""
    from .util import numeric_gate_filter
    result, visited = [], set()
    allowed = X_series | Y_series | Z_series | CU_series | SWAP_Series | {I.label, H.label}
    for index in g.topological_sorting():
        if index in visited or not numeric_gate_filter(index, g):
            continue
        if g.vs[index]['name'] not in allowed:
            continue
        path = [index]
        visited.add(index)
        while True:
            successors = set(g.successors(path[-1]))
            if len(successors) != 1:
                break
            nxt = successors.pop()
            if nxt in visited or not numeric_gate_filter(nxt, g):
                break
            cur, pre = g.vs[nxt], g.vs[path[-1]]
            if set(g.predecessors(nxt)) != {path[-1]}:
                break
            if set(cur['qubits']) != set(pre['qubits']):
                break
            if cur['name'] == I.label or pre['name'] == I.label:
                compatible = cur['name'] == pre['name']
            else:
                compatible = is_commutative(cur, pre)
            if not compatible:
                break
            path.append(nxt)
            visited.add(nxt)
        result.append(path)
    return result
