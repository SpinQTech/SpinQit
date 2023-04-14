# Copyright 2022 SpinQ Technology Co., Ltd.
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
import os
import queue
from collections import Counter
from copy import deepcopy
from typing import List, Iterable

import numpy as np
import torch
from scipy import sparse

from spinqit.backend.backend_util import _add_pauli_gate
from spinqit.primitive import generate_hamiltonian_matrix, PauliBuilder
from spinqit.backend.basebackend import BaseBackend
from spinqit.utils.function import _flatten
from spinqit.compiler.ir import IntermediateRepresentation as IR
from spinqit.compiler.ir import NodeType

dtype = torch.complex64
device = torch.device('cpu')


def torch_matrix(label, params=None):
    np_mat = IR.get_basis_gate(label).get_matrix(params)
    torch_mat = torch.from_numpy(np_mat).to(device, dtype)
    return torch_mat


def _P(x):
    return (torch_matrix('Z') ** (x / torch.pi)).to(device, dtype)


def _Rx(x):
    return (torch.cos(x / 2) * torch_matrix('I') - 1j * torch.sin(x / 2) * torch_matrix('X')).to(device, dtype)


def _Ry(x):
    return (torch.cos(x / 2) * torch_matrix('I') - 1j * torch.sin(x / 2) * torch_matrix('Y')).to(device, dtype)


def _Rz(x):
    return (torch.cos(x / 2) * torch_matrix('I') - 1j * torch.sin(x / 2) * torch_matrix('Z')).to(device, dtype)


def _U3(x):
    return _P(x[1] + x[2]) @ _Rz(-x[2]) @ _Ry(x[0]) @ _Rz(x[2]).to(device, dtype)


rotations = {
    'rx': _Rx, 'ry': _Ry, 'rz': _Rz, 'p': _P, 'u': _U3,
}


class TorchSimulatorConfig:
    def __init__(self):
        self.mqubits = None
        self.shots = None
        self.n_threads = os.cpu_count()//2

    def configure_shots(self, shots: int):
        self.shots = shots

    def configure_measure_qubits(self, mqubits: List):
        self.mqubits = mqubits

    def configure_num_thread(self, n_threads):
        self.n_threads = n_threads


class TorchResult:
    def __init__(self, ):
        self.states = None
        self.config = None
        self.__counts = None
        self.__prob = None
        self.__torch_counts = None
        self.__torch_prob = None
        self.__is_change = None

    def __str__(self):
        return f'Counts :{self.counts}, States :{self.states}, Prob :{self.probabilities}'

    def set_result(self, states, config):
        self.states = states
        self.config = config
        self.__is_change = True

    @property
    def counts(self):
        if not self.__is_change and self.__counts is not None:
            return self.__counts
        shots = self.config.shots
        if shots is None:
            shots = 1024
        probabilities, batch = self._process_prob(self.config, self.states)
        if probabilities.is_cuda:
            probabilities = probabilities.cpu()
        if not batch:
            counts = Counter(torch.multinomial(probabilities, shots, True).tolist())
            self.__counts = {bin(key)[2:].zfill(int(np.log2(len(probabilities)))): count
                             for key, count in sorted(counts.items()) if count != 0}

        else:
            self.__counts = {}
            for i in range(batch[0]):
                counts = Counter(torch.multinomial(probabilities[i], shots, True).tolist())
                self.__counts[f'batch {i}'] = {bin(key)[2:].zfill(int(np.log2(len(probabilities[i])))): count
                                               for key, count in sorted(counts.items()) if count != 0}
        self.__is_change = False
        return self.__counts

    @property
    def probabilities(self):
        if not self.__is_change and self.__prob is not None:
            return self.__prob
        probabilities, batch = self._process_prob(self.config, self.states)
        if probabilities.is_cuda:
            probabilities = probabilities.cpu()
        if not batch:
            self.__prob = {bin(key)[2:].zfill(int(np.log2(len(probabilities)))): prob.detach().numpy()
                           for key, prob in enumerate(probabilities) if abs(prob) > 1e-6}
        else:
            self.__prob = {}
            for i in range(batch[0]):
                self.__prob[f'batch {i}'] = {
                    bin(key)[2:].zfill(int(np.log2(len(probabilities)))): prob.detach().numpy()
                    for key, prob in enumerate(probabilities[i]) if abs(prob) > 1e-6}
        self.__is_change = False
        return self.__prob

    @property
    def torch_prob(self):
        if not self.__is_change and self.__torch_prob is not None:
            return self.__torch_prob
        probabilities, _ = self._process_prob(self.config, self.states)
        self.__torch_prob = probabilities
        self.__is_change = False
        return self.__torch_prob

    @property
    def torch_counts(self):
        if not self.__is_change and self.__torch_counts is not None:
            return self.__torch_counts
        shots = self.config.shots
        if shots is None:
            shots = 1024
        probabilities, batch = self._process_prob(self.config, self.states)
        length = probabilities.size(0) if not batch else probabilities.size(1)
        counts = torch.concat([torch.bincount(
            torch.multinomial(probabilities[i], shots, True),
            minlength=length
        ).reshape(1, -1) for i in range(batch[0])], dim=0)
        self.__torch_counts = counts
        self.__is_change = False
        return self.__torch_counts

    @staticmethod
    def _process_prob(config, np_states):
        qubit_num = int(np.log2(np_states.shape[-1:]))
        probabilities = torch.abs(np_states) ** 2
        higher_dim = list(probabilities.shape[:-1])
        if config.mqubits is not None:
            discard_qubits = [i for i in range(qubit_num) if i not in config.mqubits]
            discard_qubits.sort(reverse=True)
            shape = higher_dim + [2] * qubit_num
            probabilities = probabilities.reshape(shape)
            for q in discard_qubits:
                if not higher_dim:
                    probabilities = probabilities.sum(axis=q)
                else:
                    probabilities = probabilities.sum(axis=q + 1)
            if not higher_dim:
                probabilities = probabilities.reshape(-1)
            else:
                probabilities = probabilities.reshape(higher_dim[0], -1)
        return probabilities, higher_dim

    def get_random_reading(self):
        return np.random.choice(list(self.counts.keys()))


class TorchSimulator:
    """
    Using pytorch to simulate the quantum circuit
    """

    def __init__(self):
        self.result = TorchResult()

    def __call__(self, state, exe, params, config) -> TorchResult:
        """

        Args:
            state (torch.Tensor): The initial quantum state
            exe (IntermediateRepresentation): calculate graph for quantum circuit.
            params (torch.Tensor): The parameter for circuit
            config (TorchSimulatorConfig):
        Return:
            final_state:torch.Tensor

        """

        qubits_num = exe.qnum
        final_state = self.get_final_state(exe, state, params, qubits_num)
        self.result.set_result(final_state, config)
        return self.result

    def get_final_state(self, ir, state, params, qubits_num):
        vids = self._topological_sort(ir.dag)
        for i in vids:
            v = ir.dag.vs[i]
            if v['type'] == NodeType.op.value:
                _p = self._check_params(v, params)
                state = self._op_node(v, _p, state, v['qubits'], qubits_num)
            elif v['type'] == NodeType.caller.value:
                state = self._caller_node(v, v['params'], state, v['qubits'], qubits_num, ir.dag)
        return state

    def _op_node(self, v, params, state, qubits, qubits_num):
        label = v['name']
        if 'trainable' in v.attributes() and v['trainable']:
            gate = rotations[label.lower()](params)
        else:
            gate = torch_matrix(label, params)
        state = self._apply_gate(state, gate, qubits, qubits_num)
        return state

    def _dfs(self, root_index: int, graph, visited, result: List):
        successors = graph.neighbors(root_index, mode='out')
        for s in successors:
            if s not in visited:
                self._dfs(s, graph, visited, result)
        result.append(root_index)
        visited.add(root_index)

    @staticmethod
    def _topological_sort(graph) -> List[int]:
        indegree_table = [0] * graph.vcount()
        for i in range(graph.vcount()):
            indegree_table[i] = graph.vs[i].indegree()
        registers = graph.vs.select(type=NodeType.register.value)
        vids = []
        vq = queue.Queue()
        for r in registers:
            vq.put(r.index)
        while not vq.empty():
            vid = vq.get()
            vids.append(vid)
            neighbors = graph.neighbors(vid, mode="out")
            for n in neighbors:
                indegree_table[n] -= 1
                if indegree_table[n] == 0:
                    vq.put(n)
        return vids

    def _caller_node(self, v, params, state, qubits, qubits_num, graph, ):
        gname = v['name']

        def_node = graph.vs.find(gname, type=NodeType.definition.value)

        topo_sort_list = []
        visited = set()
        self._dfs(def_node.index, graph, visited, topo_sort_list)
        topo_sort_list = topo_sort_list[::-1]
        for node_idx in topo_sort_list:
            node = graph.vs[node_idx]
            if node.index != def_node.index:
                qidxes = node['qubits']
                local = [qubits[i] for i in qidxes]
                callee_params = self._check_params(node, params)
                if node['type'] == NodeType.callee.value:
                    state = self._op_node(node, callee_params, state, local, qubits_num)
                elif node['type'] == NodeType.caller.value:
                    state = self._caller_node(node, callee_params, state, local, qubits_num, graph)
        return state

    def _apply_gate(self, state: torch.Tensor, gate: torch.Tensor,
                    qubit_idx: List[int], num_qubits: int) -> torch.Tensor:

        if not isinstance(qubit_idx, Iterable):
            qubit_idx = [qubit_idx]

        swap_ops = self._get_swap_ops(qubit_idx, num_qubits)
        state = self._apply_gate_fn(state, gate, swap_ops, num_qubits, qubit_idx, )
        return state

    def _apply_gate_fn(self, state, gate, swap_ops, num_qubits, qubit_idx, ):
        higher_dims = list(state.shape[:-1])
        num_higher_dims = len(higher_dims)

        num_acted_qubits = len(qubit_idx)
        perm = list(range(num_higher_dims + 5))
        perm[num_higher_dims+1], perm[num_higher_dims+3] = perm[num_higher_dims+3], perm[num_higher_dims+1]

        state = self._reshape_state_dim(state, swap_ops, higher_dims, num_qubits, perm)
        state = torch.reshape(state, higher_dims + [2 ** num_acted_qubits, 2 ** (num_qubits - num_acted_qubits)])
        state = torch.matmul(gate, state)
        swap_ops.reverse()
        state = self._reshape_state_dim(state, swap_ops, higher_dims, num_qubits, perm)
        state = torch.reshape(state, higher_dims + [2 ** num_qubits])
        return state

    @staticmethod
    def _get_swap_ops(qubit_idx, num_qubits):
        origin_seq = list(range(num_qubits))
        seq_for_acted = qubit_idx + [x for x in origin_seq if x not in qubit_idx]
        swapped = [False] * num_qubits
        swap_ops = []
        for idx in range(num_qubits):
            if not swapped[idx]:
                next_idx = idx
                swapped[next_idx] = True
                while not swapped[seq_for_acted[next_idx]]:
                    swapped[seq_for_acted[next_idx]] = True
                    if next_idx < seq_for_acted[next_idx]:
                        swap_ops.append((next_idx, seq_for_acted[next_idx]))
                    else:
                        swap_ops.append((seq_for_acted[next_idx], next_idx))
                    next_idx = seq_for_acted[next_idx]
        return swap_ops

    @staticmethod
    def _reshape_state_dim(state, swap_ops, higher_dims, num_qubits, perm):
        dim = 2
        for swap_op in swap_ops:
            shape = higher_dims.copy()
            last_idx = -1
            for idx in swap_op:
                shape.append(dim ** (idx - last_idx - 1))
                shape.append(dim)
                last_idx = idx
            shape.append(dim ** (num_qubits - last_idx - 1))
            state = state.reshape(shape).permute(perm)
        return state

    @staticmethod
    def _check_params(v, params, ):
        if 'trainable' in v.attributes() and v['trainable']:
            if params is None:
                raise ValueError(
                    'There are no trainable parameters in the quantum circuit.'
                )
            func = v['trainable']
            _p = func(params)
        elif 'pindex' in v.attributes() and v['pindex'] is not None:
            pidx = v['pindex']
            _p = []
            start = 0
            for func in (v['params']):
                arg_count = func.__code__.co_argcount
                if arg_count == 0:
                    _p.append(func())
                else:
                    try:
                        _p.append(func(tuple(params[i] for i in pidx[start:start + arg_count])))
                    except TypeError:
                        _p.append(func(*tuple(params[i] for i in pidx[start:start + arg_count])))
                    start += arg_count
        else:
            _p = None if ('params' not in v.attributes() or not v['params']) else v['params']
        return _p

    @staticmethod
    def set_device(new_device):
        global device
        if isinstance(new_device, str):
            device = torch.device(new_device)
        elif isinstance(new_device, torch.device):
            device = new_device
        else:
            raise ValueError(
                'The torch backend device is expected type `str` or `torch.device` '
                f'but got type `{type(new_device)}`. '
            )

    @staticmethod
    def set_dtype(new_dtype):
        global dtype
        dtype = new_dtype


def torch_pauli_expectation(pauli_string, probabilities):
    imat = sparse.csr_matrix(np.eye(2))
    zmat = sparse.csr_matrix(np.array([[1,0],[0,-1]]))
    mat = 1

    for i, ch in enumerate(pauli_string):
        if ch.upper() in ['X', 'Y', 'Z']:
            mat = sparse.kron(zmat, mat, format='csr')
        elif ch.upper() == 'I':
            mat = sparse.kron(imat, mat, format='csr')
        else:
            raise ValueError('The input string is not a Pauli string')

    f = torch.tensor(mat.diagonal())
    if len(probabilities.shape) < 2:
        probabilities = probabilities.unsqueeze(0)
    expect_val = (probabilities * f).sum(dim=1)
    return expect_val


class TorchSimulatorBackend(BaseBackend):
    def __init__(self):
        super().__init__()

        self.simulator = TorchSimulator()

    def execute(self, ir, config, state=None, params=None):
        qubits_num = ir.qnum
        if state is None:
            state = torch.tensor([1.0] + [0.0] * (2 ** qubits_num - 1)).to(device, dtype)
        else:
            if int(np.log2(state.shape[-1:])) != qubits_num:
                raise ValueError(
                    f'The number of qubits of state is wrong. Expected {qubits_num}, '
                    f'but got {int(np.log2(len(state)))}'
                )
            if not isinstance(state, torch.Tensor):
                state = torch.from_numpy(state)
            state = state.to(device, dtype)
        if params is not None:
            params = self.process_params(params)
        torch.set_num_threads(config.n_threads)
        result = self.simulator(state, ir, params, config)
        return result

    def expval(self, ir, config, hamiltonian, state=None, params=None):
        if isinstance(hamiltonian, (np.ndarray, sparse.csr_matrix)):
            hamiltonian = self._process_hamiltonian(hamiltonian)
            state = self.execute(ir, config, state=state, params=params).states

            b = state.conj()
            if len(state.shape) > 1:
                k = hamiltonian @ state.T
                value = torch.real(torch.diagonal(b @ k))
            else:
                k = hamiltonian @ state
                value = torch.real(b @ k)
        elif isinstance(hamiltonian, list):
            value = 0.0
            mqubits = config.mqubits if config.mqubits is not None else list(range(ir.qnum))
            for i, (pstr, coeff) in enumerate(hamiltonian):
                h_part = PauliBuilder(pstr).to_gate()
                execute_ir = deepcopy(ir)
                _add_pauli_gate(h_part, mqubits, execute_ir)
                result = self.execute(execute_ir, config, state=state, params=params)
                value += coeff * torch_pauli_expectation(pstr, result.torch_prob)
        else:
            raise NotImplementedError
        return value

    def grads(self, ir, params, hamiltonian, config, method, state=None):
        if method != 'backprop':
            raise NotImplementedError('The torch backend only supported `backprop` grad_method')
        params = self.process_params(params)
        val = self.expval(ir, config, hamiltonian, state, params)
        val.backward()
        return val.detach().numpy(), params.grad.detach().numpy()

    def update_param(self, ir=None, new_params=None):
        """
        Set the new_params to the backend and Update the trainable params
        For torch backend It is not necessary
        """
        if new_params is not None:
            if isinstance(new_params, torch.Tensor):
                if new_params.is_cuda:
                    new_params = new_params.cpu()
                if new_params.requires_grad:
                    new_params = new_params.detach().numpy()
            for v in ir.dag.vs:
                if v['trainable']:
                    func = v['trainable']
                    v['params'] = list(_flatten((func(new_params).tolist(),)))

    def set_dtype(self, new_dtype):
        self.simulator.set_dtype(new_dtype)

    def set_device(self, new_device):
        self.simulator.set_device(new_device)

    @staticmethod
    def process_params(new_params):
        if not isinstance(new_params, torch.Tensor):
            if isinstance(new_params, np.ndarray):
                new_params = torch.from_numpy(new_params)
            else:
                new_params = torch.tensor(new_params)
        if not new_params.requires_grad:
            new_params = new_params.requires_grad_()
        return new_params

    @staticmethod
    def _scipy_sparse_mat_to_torch_sparse_tensor(sparse_mx):
        """
        Convert scipy.sparse.csr_matrix to the torch.sparse.coo_tensor.

        Note:
            There are some type of torch sparse tensor cannot be applied on cuda device or used sparse grad
        """
        sparse_mx = sparse_mx.tocoo()
        indices = torch.from_numpy(
            np.vstack((sparse_mx.row, sparse_mx.col)).astype(np.int64))
        values = torch.from_numpy(sparse_mx.data)
        shape = torch.Size(sparse_mx.shape)
        return torch.sparse_coo_tensor(indices, values, shape).to(device, dtype)

    def _process_hamiltonian(self, hamiltonian, ):
        if hamiltonian is not None:
            if not isinstance(hamiltonian, (list, sparse.csr_matrix, np.ndarray)):
                raise ValueError('The hamiltonian is not supported, should be a list of pauli string with coefficient'
                                 f'or use `generate_hamiltonian_matrix` to construct `sparse.csr_matrix` or `np.ndarray`, '
                                 f'but got {type(hamiltonian)}')
            if isinstance(hamiltonian, list):
                hamiltonian = generate_hamiltonian_matrix(hamiltonian)
            hamiltonian = self._scipy_sparse_mat_to_torch_sparse_tensor(hamiltonian)
        return hamiltonian
