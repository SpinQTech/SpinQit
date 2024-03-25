# Copyright 2023 SpinQ Technology Co., Ltd.
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

from typing import List, Iterable

import numpy as np
from autograd import elementwise_grad as egrad

from spinqit import X, Y, Z, I, Rx, Ry, Rz, P
from spinqit.compiler.ir import IntermediateRepresentation as IR
from spinqit.utils.function import _topological_sort, _dfs, requires_grad
from .param_shift import parameter_shift


def grad_func(ir, params, config, backend, measure_op, res, grad_method):
    if grad_method == 'param_shift':
        backward_fn = parameter_shift(ir, params, config, backend, measure_op)
    elif grad_method == 'adjoint_differentiation':
        backward_fn = adjoint_differentiation(ir, params, measure_op, res)
    else:
        def backward_fn(*args):
            raise ValueError(f'The method {grad_method} is not supported for `spinq` backend now')

    return backward_fn


def adjoint_differentiation(ir, params, measure_op, res):

    def _op_node(gname, qubit_num, bra, ket, grads, func, node_params, qubits, total_params, dy):
        label = gname

        generator = {
            Rx.label: -0.5 * X.get_matrix(),
            Ry.label: -0.5 * Y.get_matrix(),
            Rz.label: -0.5 * Z.get_matrix(),
            P.label: 0.5 * (I.get_matrix() - Z.get_matrix()),
        }
        # Get the gate matrix
        if label in generator:
            mat = IR.get_basis_gate(label).get_matrix(node_params)
        else:
            mat = IR.get_basis_gate(label).get_matrix()
        # apply the dagger gate to the ket
        ket = _apply_gate(ket, mat.conj().T, qubits, qubit_num)
        # If gate is trainable gate, calculate the coefficient of the params and the gradients of the gate.
        if func is not None and node_params is not None:
            for i, param in enumerate(node_params):
                if requires_grad(param):
                    func = func[i]
                    coeffs = egrad(func)(total_params)
                    gen_mat = generator[label]
                    d_theta = 1j * gen_mat @ mat
                    tmp_ket = _apply_gate(ket, d_theta, qubits, qubit_num)
                    g = np.real(bra.reshape(-1) @ tmp_ket.reshape(-1))
                    if not np.allclose(g, 0):
                        if not g.shape:
                            g = g.reshape(-1)
                        for key, _coeff in enumerate(coeffs):
                            grads[key] += _coeff * 2 * np.tensordot(g, dy.real, axes=[[0], [0]])
        # apply the dagger gate to the bra.
        bra = _apply_gate(bra.conj(), mat.conj().T, qubits, qubit_num).conj()
        return bra, ket

    # TODO fix the gradients calculation of caller node in the future
    def _caller_node(gname, qubits_num, bra, ket, grads, func, params, qubits, graph, total_params, dy):
        def_node = graph.vs.find(gname, type=2)

        topo_sort_list = []
        visited = set()
        _dfs(def_node.index, graph, visited, topo_sort_list)

        for node_idx in topo_sort_list:
            node = graph.vs[node_idx]
            if node.index != def_node.index:
                local = [qubits[i] for i in node['qubits']]
                plambda = node['params'] if 'params' in node.attributes else None
                callee_params = [f(params) for f in plambda] if not plambda else []
                if node['type'] == 3:
                    bra, ket = _op_node(node['name'], qubits_num,
                                        bra, ket,
                                        grads,
                                        func, callee_params, local,
                                        total_params, dy)
                elif node['type'] == 1:
                    bra, ket = _caller_node(node['name'], qubits_num,
                                            bra, ket,
                                            grads,
                                            func, callee_params,
                                            local, graph,
                                            total_params, dy)
        return bra, ket

    def _apply_gate(state: np.ndarray, gate: np.ndarray,
                    qubit_idx: List[int], num_qubits: int) -> np.ndarray:
        # higher_dims = list(state.shape[:-1])
        # num_higher_dims = len(higher_dims)

        if not isinstance(qubit_idx, Iterable):
            qubit_idx = [qubit_idx]

        shape = [2] * (len(qubit_idx) * 2)
        state_axes = qubit_idx
        mat = np.reshape(gate, shape)
        axes = (np.arange(-len(qubit_idx), 0), state_axes)
        tdot = np.tensordot(mat, state, axes)

        unused_idxs = [idx for idx in range(num_qubits) if idx not in qubit_idx]
        perm = list(qubit_idx) + unused_idxs
        inv_perm = np.argsort(perm)  # argsort gives inverse permutation
        return np.transpose(tdot, inv_perm)

    def backward_fn(dy):
        if measure_op.mtype != 'expval':
            raise ValueError(
                'The adjoint differentiation method only support the `expval` measurement, '
                'and the hamiltonian should be `matrix` or `sparse matrix`, '
                'may use spinqit.generate_hamiltonian_matrix. '
                'For more details, see spinqit.algorithm.loss.measurement.MeasureOp.'
            )

        if isinstance(measure_op.hamiltonian, list):
            raise ValueError(
                'The `adjoint_differentiation` grad_method only support the matrix hamiltonian'
            )

        if not getattr(res, 'states', None):
            raise ValueError(
                'There is no `states` for `adjoint_differentiation`. '
                'The backend may not support the states measurement. '
                'Checkout the backend, use the simulator backend.'
            )

        ket = np.array(res.states)
        bra = ket.conj() @ measure_op.hamiltonian
        ket = ket.reshape([2]*ir.qnum)
        bra = bra.reshape([2]*ir.qnum)
        grads = []
        for param in params:
            grads.append(np.zeros_like(param))

        vids = _topological_sort(ir.dag)

        if not dy.shape:
            dy = dy.reshape(-1)

        for i in vids[::-1]:
            v = ir.dag.vs[i]
            func = v['func'] if 'func' in v.attributes() else None
            node_params = v['params'] if 'params' in v.attributes() else []
            qubits = v['qubits']
            gname = v['name']
            if v['type'] == 0:
                bra, ket = _op_node(gname, ir.qnum,
                                    bra, ket,
                                    grads,
                                    func, node_params, qubits,
                                    params, dy)
            elif v['type'] == 1:
                bra, ket = _caller_node(gname, ir.qnum,
                                        bra, ket,
                                        grads,
                                        func, node_params,
                                        qubits, ir.dag,
                                        params, dy)
        return grads

    return backward_fn
