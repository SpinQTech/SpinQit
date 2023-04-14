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
from igraph import Graph, Vertex
from ..ir import IntermediateRepresentation

def get_paths(graph: Graph, filter: Callable) -> List:
    """ Collect all the paths consist of valid vertices.
        Return one path every time because the vertex index may be modified.
    """
    result = []
    if filter is None:
        return result

    visited = set()
    vs = graph.topological_sorting()
    for vertex in vs:
        if not filter(vertex, graph) or vertex in visited:
            continue
        visited.add(vertex)
        path = [vertex]
        slist = graph.successors(vertex)
        
        while len(set(slist))==1 and filter(slist[0], graph) and not slist[0] in visited:
            cur = slist[0]
            path.append(cur)
            visited.add(cur)
            slist = graph.successors(cur)

        if len(path) > 0:
            result.append(path)

    return result

def get_matrix(gate: str, params: List =None):
    for basis in IntermediateRepresentation.basis_set:
        if gate == basis.label:
            return basis.get_matrix(params)

def get_qubits(v: Vertex) -> List[int]:
    in_edges = v.in_edges()
    in_edges.sort(key = lambda k: k.index)
    result = []
    for e in in_edges:
        if 'qubit' in e.attributes() and e['qubit'] is not None:
            result.append(e['qubit'])
    return result