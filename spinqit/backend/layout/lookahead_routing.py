# Copyright 2024 SpinQ Technology Co., Ltd.
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
from typing import List, Tuple, Dict
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
import numpy as np

from .layout import Layout
from spinqit.model import RoutingError

def _calculate_physical_distance(topo: List) -> np.ndarray:
    row = []
    col = []
    data = []
    size = 0
    for connection in topo:
        row.append(connection[0])
        size = max(size, connection[0])
        col.append(connection[1])
        size = max(size, connection[1])
        data.append(1)
    size += 1
    topo_mat = csr_matrix((data, (row, col)), shape=(size, size), dtype=int)
    dist_matrix = dijkstra(csgraph=topo_mat, directed=True, indices=range(size))
    return dist_matrix

def _transform_gates(gates: List, swap_map: Dict, dist_mat: np.ndarray) -> Tuple:
    '''If one gate cannot be applied, all the following gates should be blocked.
       Each gate is represented by (gate_id, qubits). 
    '''
    remaining_gates = []
    updated_gates = {}
    for gate in gates:
        if len(remaining_gates) > 0:
            remaining_gates.append(gate)
            continue

        qubits = gate[1]
        cur_qubits = tuple([swap_map[q] for q in qubits])

        if len(qubits) == 1 and qubits != cur_qubits:
            updated_gates[gate[0]] = cur_qubits
        if len(qubits) == 2:
            if dist_mat[cur_qubits[0]][cur_qubits[1]] > 1:
                remaining_gates.append(gate)
            elif qubits != cur_qubits:
                updated_gates[gate[0]] = cur_qubits
        elif len(qubits) == 3:
            pairs = [(cur_qubits[i], cur_qubits[j]) for i in range(len(qubits)) for j in range(i+1, len(qubits))]
            for pair in pairs:
                if dist_mat[pair[0]][pair[1]] > 1:
                    remaining_gates.append(gate)
                    break
            else: 
                if qubits != cur_qubits:
                    updated_gates[gate[0]] = cur_qubits
    return remaining_gates, updated_gates

def _evaluate_step(step: Tuple, ref_gates: List):
    new_swaps = step[0]
    remaining_gates = step[1]
    return len(ref_gates) - len(remaining_gates) - 3 * len(new_swaps)

def _calculate_layout_distance(gates: List, swap_map: Dict, dist_mat: np.ndarray):
    total = 0
    for gate in gates:
        logical_qubits = gate[1]
        if len(logical_qubits) > 1:
            pairs = [(swap_map[logical_qubits[i]], swap_map[logical_qubits[j]]) for i in range(len(logical_qubits)) for j in range(i+1,len(logical_qubits))]
            for pair in pairs:
                total += dist_mat[pair[0]][pair[1]]
    return total

def _update_logical_map(swaps: List, swap_map: Dict):
    for swap in swaps:
        swap_map[swap[0]], swap_map[swap[1]] = swap_map[swap[1]], swap_map[swap[0]]

def _locate_swap(swap_logical_qubits: List, gates: List) -> Tuple:
    '''
       swap_logical_qubits: the logical qubits of a swap gate
       gates: the remaining gates after adding the swap gate in the topological order
       Each gate is represented by (gate_ids, qubits).
       Return the gate_ids (caller, callee) to locate the swap gate.
    '''
    for gate in gates:
        qubits = set(gate[1])
        if swap_logical_qubits[0] in qubits:
            return gate[0]
        if swap_logical_qubits[1] in qubits:
            return gate[0]  
    return None

def _search_best_swap(gates: List, edge_list: List, mapping: Dict, dist_mat: np.ndarray, depth: int, width: int) -> Tuple:
    '''Return swap gates to add, remaining gates, and the gates to update.
    '''
    if not gates or depth == 0:
        return {}, gates, {}

    def _swap_key(swap):
        swap_map = mapping.copy()
        _update_logical_map([swap], swap_map)
        return _calculate_layout_distance(gates, swap_map, dist_mat)

    # connections between logical qubits
    rankings = sorted(edge_list, key=_swap_key)
    
    best_swap, best_step, best_result, best_updates = None, None, None, None
    original_distance = _calculate_layout_distance(gates, mapping, dist_mat)

    for rank, swap_log_qubits in enumerate(rankings):
        post_mapping = mapping.copy()
        _update_logical_map([swap_log_qubits], post_mapping)
        # update gates after adding swap gates
        remaining_gates, updated_gates = _transform_gates(gates, post_mapping, dist_mat)

        next_step = _search_best_swap(remaining_gates, edge_list, post_mapping, dist_mat, depth-1, width)
       
        if next_step is None:
            continue

        if best_swap is None:
            best_swap = swap_log_qubits
            best_step = next_step
            best_result = _evaluate_step(best_step, gates)
            best_updates = updated_gates
        else:
            next_result = _evaluate_step(next_step, gates)
            if next_result > best_result:
                best_swap = swap_log_qubits
                best_step = next_step
                best_result = next_result
                best_updates = updated_gates
        
        swap_qubits = []
        for pq in best_step[0].values():
            swap_qubits.extend(pq)

        _update_logical_map(swap_qubits, post_mapping)
        
        possible_remaining = best_step[1]
        possible_updates = best_step[2]
        
        if (
            rank >= min(width, len(rankings) - 1)
            and best_swap is not None
            and (
                len(possible_updates) > depth
                or len(possible_remaining) < len(gates)
                or _calculate_layout_distance(possible_remaining, post_mapping, dist_mat) < original_distance
            )
        ):
            break

    if best_swap is None:
        return None
    
    # swap_gates = {position: [swaps]}
    swap_gates = best_step[0]
      
    swap_pos = _locate_swap(best_swap, gates)
    if swap_pos in swap_gates:
        swap_gates[swap_pos].insert(0, best_swap)
    else:
        swap_gates[swap_pos] = [best_swap]

    remaining_gates = best_step[1]
    best_updates.update(best_step[2])

    return swap_gates, remaining_gates, best_updates 

def generate_lookahead_routing(gates: List[Tuple], topology: List[Tuple], mapping: Layout, search_depth: int = 4, search_width: int = 4):
    '''
    Parameters:
        gates: a list of (vertex_index, logical_qubits)
        topology: a list of physical connections
        mapping: initial mapping from physical qubits to logical qubits and vice versa
        search_depth: the depth of recursion
        search_width: the number of edges to search
    '''
    connections = []
    # calculate distance between logical qubits
    for t in topology:
        if t[0] in mapping.phy_to_log and t[1] in mapping.phy_to_log:
            pair = (mapping.phy_to_log[t[0]], mapping.phy_to_log[t[1]])
            connections.append(pair)
    dist_matrix = _calculate_physical_distance(connections)

    #generate undirected connections between logical qubits
    coupling_list = []
    connection_set = set(connections)
    for pair in connections:
        reverse_pair = (pair[1], pair[0])
        if reverse_pair in connection_set:
            ordered_pair = tuple(sorted(pair))
            coupling_list.append(ordered_pair)

    qubit_num = len(mapping.log_to_phy)
    swap_map = {i:i for i in range(qubit_num)}
    
    gates_remaining, gates_updated = _transform_gates(gates, swap_map, dist_matrix)
    
    swaps = {}
    prev_remaining = 0
    while gates_remaining:
        if prev_remaining == len(gates_remaining):
            raise RoutingError('Some multi-qubit gates cannot be handled')
        prev_remaining = len(gates_remaining)
        swaps_added, gates_remaining, gates_mapped = _search_best_swap(gates_remaining, coupling_list, swap_map, dist_matrix, search_depth, search_width)

        swap_qubits = []
        sorted_keys = sorted(swaps_added.keys())
        for key in sorted_keys:
            swap_qubits.extend(swaps_added[key])
            if key in swaps:
                swaps[key].extend(swaps_added[key])
            else:
                swaps[key] = swaps_added[key]
        
        gates_updated.update(gates_mapped)
        _update_logical_map(swap_qubits, swap_map)
    return swaps, gates_updated