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
import functools
from collections import Counter
from copy import deepcopy
from typing import List, Iterable

from autoray import numpy as ar
import numpy as onp
from scipy import sparse

from spinqit.backend.backend_util import _add_pauli_gate
from spinqit.primitive.pauli_builder import PauliBuilder
from .basebackend import BaseBackend
from spinqit.grad import grad_func_torch
from spinqit.model.parameter import LazyParameter, Parameter
from spinqit.utils.function import _topological_sort, _dfs, requires_grad
from spinqit.compiler.ir import IntermediateRepresentation as IR
try:
    import torch
    dtype = torch.complex64
    device = torch.device('cpu')
    IMPORTED = True
except ImportError:
    IMPORTED = False


def torch_matrix(label, params=None):
    np_mat = IR.get_basis_gate(label).get_matrix(params)
    torch_mat = torch.from_numpy(np_mat).to(device, dtype)
    return torch_mat


def _P(x):
    return torch.diag(torch.tensor([1, -1], dtype=dtype) ** (x / torch.pi)).to(device)


def _Rx(x):
    return (torch.cos(x / 2) * torch_matrix('I') - 1j * torch.sin(x / 2) * torch_matrix('X')).to(device, dtype)


def _Ry(x):
    return (torch.cos(x / 2) * torch_matrix('I') - 1j * torch.sin(x / 2) * torch_matrix('Y')).to(device, dtype)


def _Rz(x):
    return (torch.cos(x / 2) * torch_matrix('I') - 1j * torch.sin(x / 2) * torch_matrix('Z')).to(device, dtype)


def _U3(x):
    return (_P(x[1] + x[2]) @ _Rz(-x[2]) @ _Ry(x[0]) @ _Rz(x[2])).to(device, dtype)


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
        if isinstance(new_dtype, str):
            dtype_map = {'complex128': torch.complex128,
                         'complex64': torch.complex64}
            new_dtype = dtype_map[new_dtype]
        dtype = new_dtype


def lazy_property(fn):
    """
    A lazy property decorator.
    The function decorated is called the first time to retrieve the result and
    then that calculated result is used the next time you access the value.
    """
    attr = '_lazy__' + fn.__name__

    @property
    def _lazy_property(self):
        _attr = hasattr(self, attr)
        _changed = hasattr(self, '__is_change')
        if _changed or not _attr:
            setattr(self, attr, fn(self))
            setattr(self, '__is_change', False)
        return getattr(self, attr)

    return _lazy_property


class TorchResult:
    def __init__(self, ):
        self.states = None
        self.config = None
        self.__is_change = None

    def __str__(self):
        return f'Counts :{self.counts}, States :{self.states}, Prob :{self.probabilities}'

    def set_result(self, states, config):
        self.states = states
        self.config = config
        self.__is_change = True

    @lazy_property
    def counts(self):
        shots = self.config.shots
        if shots is None:
            shots = 1024
        probabilities, batch = self._process_prob(self.config, self.states)
        probabilities = probabilities.cpu()
        if not batch:
            counts = Counter(torch.multinomial(probabilities, shots, True).tolist())
            return {bin(key)[2:].zfill(int(onp.log2(len(probabilities)))): count
                    for key, count in sorted(counts.items()) if count != 0}
        else:
            _counts = {}
            for i in range(batch[0]):
                counts = Counter(torch.multinomial(probabilities[i], shots, True).tolist())
                _counts[f'batch {i}'] = {
                    bin(key)[2:].zfill(int(onp.log2(len(probabilities[i])))): count
                    for key, count in sorted(counts.items()) if count != 0}
            return _counts

    @lazy_property
    def probabilities(self):
        probabilities, _ = self._process_prob(self.config, self.states)
        probabilities = probabilities.cpu()
        prob_dict = {}
        width = int(onp.log2(len(probabilities)))
        for key, prob in enumerate(probabilities):
            if prob > 1e-15:
                prob_dict[bin(key)[2:].zfill(width)] = prob.item()
        return prob_dict

    @lazy_property
    def raw_probabilities(self):
        probabilities, _ = self._process_prob(self.config, self.states)
        return probabilities

    @staticmethod
    def _process_prob(config, np_states):
        qubit_num = int(onp.log2(np_states.shape[-1:]))
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
        return onp.random.choice(list(self.counts.keys()))


class TorchSimulator:
    """
    Using pytorch to simulate the quantum circuit
    """

    def __init__(self):
        self.result = TorchResult()

    def __call__(self, exe, config) -> TorchResult:
        """

        Args:
            exe (IntermediateRepresentation): calculate graph for quantum circuit.
            config (TorchSimulatorConfig):
        Return:
            final_state:torch.Tensor

        """
        torch.set_num_threads(config.n_threads)
        state = torch.zeros(2 ** exe.qnum).to(device, dtype)
        state[0] = 1
        final_state = self.get_final_state(exe, state)
        self.result.set_result(final_state, config)
        return self.result

    def get_final_state(self, ir, state):
        vids = _topological_sort(ir.dag)
        for i in vids:
            v = ir.dag.vs[i]
            node_params = v['params'] if 'params' in v.attributes() else []
            if v['type'] == 0:
                if v['name'] == 'StateVector':
                    state = self._state_vector_node(node_params, ir.qnum)
                else:
                    state = self._op_node(v['name'], node_params, state, v['qubits'], ir.qnum)
            elif v['type'] == 1:
                state = self._caller_node(v['name'], node_params, state, v['qubits'], ir.qnum, ir.dag)
        return state

    @staticmethod
    def _state_vector_node(states, qubits_num):
        if len(states) == 1:
            state = torch.as_tensor(states[0], device=device, dtype=dtype)
        else:
            state = torch.as_tensor(states, device=device, dtype=dtype)

        if not torch.allclose((state ** 2).sum().real, torch.tensor(1., dtype=state.real.dtype)):
            raise ValueError(
                f'The `StateVector` is not a quantum state, expected norm(state) to be 1, but got {(state ** 2).sum().real}'
            )

        if state.size(-1) != 2 ** qubits_num:
            padding = torch.zeros(
                (
                    (state.size(0), 2 ** qubits_num - state.size(-1)) if len(state.size()) > 1
                    else (2 ** qubits_num - state.size(-1))
                )
            )
            state = torch.concat((state, padding), dim=0)

        return state

    def _op_node(self, label, params, state, qubits, qubits_num):
        # The trainable gate used the torch rewrite gate function, otherwise the used the spinqit.gate.matrix and
        # convert to the torch tensor.
        if params is not None and any((isinstance(p, torch.Tensor) and p.requires_grad is True) for p in params):
            if isinstance(params, list) and len(params) == 1:
                params = params[0]
            gate = rotations[label.lower()](params)
        else:
            gate = torch_matrix(label, params)
        state = self._apply_gate(state, gate, qubits, qubits_num)
        return state

    def _caller_node(self, label, params, state, qubits, qubits_num, graph, ):
        def_node = graph.vs.find(label, type=2)

        topo_sort_list = []
        visited = set()
        _dfs(def_node.index, graph, visited, topo_sort_list)
        topo_sort_list = topo_sort_list[::-1]
        for node_idx in topo_sort_list:
            node = graph.vs[node_idx]
            if node.index != def_node.index:
                local = [qubits[i] for i in node['qubits']]
                plambda = None if 'params' not in node.attributes() else node['params']
                if 'pindex' in node.attributes() and node['pindex'] is not None:
                    try:
                        p = [f(*[params[idx] for idx in node['pindex']]) for f in plambda]
                    except Exception:
                        p = [f([params[idx] for idx in node['pindex']]) for f in plambda]
                    callee_params = [] if not plambda else p
                else:
                    callee_params = [] if not plambda else [f(params) for f in plambda]
                if node['type'] == 3:
                    state = self._op_node(node['name'], callee_params, state, local, qubits_num)
                elif node['type'] == 1:
                    state = self._caller_node(node['name'], callee_params, state, local, qubits_num, graph)
        return state

    def _apply_gate(self, state, gate, qubit_idx: List[int], num_qubits: int):

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


def torch_pauli_expectation(pauli_string, probabilities):
    i_eigvals = torch.tensor([1., 1], dtype=probabilities.dtype, device=probabilities.device)
    z_eigvals = torch.tensor([1., -1], dtype=probabilities.dtype, device=probabilities.device)
    mat = []

    for i, ch in enumerate(pauli_string):
        if ch.upper() in ['X', 'Y', 'Z']:
            mat.append(z_eigvals)
        elif ch.upper() == 'I':
            mat.append(i_eigvals)
        else:
            raise ValueError('The input string is not a Pauli string')

    f = functools.reduce(torch.kron, mat)
    if len(probabilities.shape) < 2:
        probabilities = probabilities.unsqueeze(0)
    expect_val = (probabilities * f).sum(dim=1)
    return expect_val[0]


class TorchSimulatorBackend(BaseBackend):
    def __init__(self):
        super().__init__()

        self.simulator = TorchSimulator()

    def execute(self, ir, config):
        result = self.simulator(ir, config)
        return result

    def get_value_and_grad_fn(self, ir, config, measure_op=None, place_holder=None, grad_method=None):
        if not IMPORTED:
            raise ImportError(
                'The torch has not been installed, use other backend or try to install torch.'
            )
        self.check_node(ir, place_holder)
        ir = deepcopy(ir)

        def value_and_grad_fn(params):
            if grad_method == 'backprop':
                execute_grad_mode = torch.enable_grad
            else:
                execute_grad_mode = torch.no_grad
            with execute_grad_mode():
                params_for_grad = self.process_params(params)
                self.update_param(ir, params_for_grad)
                val, _ = self.evaluate(ir, config, measure_op)
                backward_fn = grad_func_torch(ir, params_for_grad, config, self, measure_op, val, grad_method)
            return val.cpu().detach().numpy() if hasattr(val, 'cpu') else val, backward_fn

        return value_and_grad_fn

    def evaluate(self, ir, config, measure_op):
        if measure_op is None:
            raise ValueError(
                'The measure_op should not be None.'
            )
        if isinstance(measure_op.hamiltonian, list):
            value = 0.0
            hamiltonian = measure_op.hamiltonian
            mqubits = config.mqubits if config.mqubits is not None else list(range(ir.qnum))
            for i, (pstr, coeff) in enumerate(hamiltonian):
                h_part = PauliBuilder(pstr).to_gate()
                node_idx = _add_pauli_gate(h_part, mqubits, ir)
                result = self.execute(ir, config)
                ir.remove_nodes(node_idx)
                value += coeff * torch_pauli_expectation(pstr, result.raw_probabilities)
            return value, None
        else:
            if measure_op.mqubits is not None:
                config.configure_measure_qubits(measure_op.mqubits)
            res = self.execute(ir, config)
            if measure_op.mtype == 'expval':
                hamiltonian = measure_op.hamiltonian
                if not isinstance(hamiltonian, (onp.ndarray, sparse.csr_matrix)):
                    raise ValueError(
                        f'The hamiltonian type is wrong. '
                        f'Expected `np.ndarray, sparse.csr_matrix, list`, but got `{type(hamiltonian)}`'
                    )
                if isinstance(hamiltonian, onp.ndarray):
                    hamiltonian = torch.as_tensor(hamiltonian, dtype, device)
                elif isinstance(hamiltonian, sparse.csr_matrix):
                    hamiltonian = self._scipy_sparse_mat_to_torch_sparse_tensor(hamiltonian)
                else:
                    hamiltonian = hamiltonian.to(device, dtype)
                state = res.states
                b = state.conj()
                if len(state.shape) > 1:
                    k = hamiltonian @ state.T
                    value = torch.real(torch.diagonal(b @ k))
                else:
                    k = hamiltonian @ state
                    value = torch.real(b @ k)
            elif measure_op.mtype == 'prob':
                value = res.raw_probabilities
            elif measure_op.mtype == 'count':
                value = res.counts
            elif measure_op.mtype == 'state':
                value = res.states
            else:
                raise ValueError(
                    f'The wrong measure_op.mtype expected `prob`, `expval`, `count`, `state`, but got {measure_op.mtype}'
                )
            return value, res

    def update_param(self, ir=None, new_params=None):
        """
        Set the new_params to the backend and Update the trainable params
        """
        if new_params is not None:
            for v in ir.dag.vs:
                if v['type'] in [0, 1] and 'func' in v.attributes() and v['func']:
                    # v['func'] indicates that the parameter comes from the outside
                    func = v['func']
                    _params = []
                    for f in func:
                        if callable(f):
                            _p = f(new_params)
                        else:
                            _p = torch.as_tensor(f)
                        _params.append(_p)

                    v['params'] = _params

    @staticmethod
    def process_params(new_params):
        """
        This function transform the trainable data to the torch.Tensor(requires_grad=True) for parameterized circuit.
        """

        execute_params = []
        for param in new_params:
            trainable = requires_grad(param)
            execute_params.append(ar.asarray(param, like='torch').requires_grad_(trainable))
        return execute_params

    @staticmethod
    @functools.lru_cache
    def check_node(ir, place_holder):
        if place_holder is not None:
            for v in ir.dag.vs:
                if v['type'] in [0, 1] and 'params' in v.attributes() and v['params'] is not None:
                    params = v['params']
                    record_function = []
                    for p in params:
                        if isinstance(p, LazyParameter):
                            record_function.append(p.get_function(place_holder))
                        else:
                            record_function.append(torch.as_tensor(p))
                    v['func'] = record_function if len(record_function) > 0 else None

    @staticmethod
    def _scipy_sparse_mat_to_torch_sparse_tensor(sparse_mx):
        """
        Convert scipy.sparse.csr_matrix to the torch.sparse.coo_tensor.

        Note:
            There are some type of torch sparse tensor cannot be applied on cuda device or used sparse grad
        """
        sparse_mx = sparse_mx.tocoo()
        indices = torch.from_numpy(
            onp.vstack((sparse_mx.row, sparse_mx.col)).astype(onp.int64))
        values = torch.from_numpy(sparse_mx.data)
        shape = torch.Size(sparse_mx.shape)
        return torch.sparse_coo_tensor(indices, values, shape).to(device, dtype)
