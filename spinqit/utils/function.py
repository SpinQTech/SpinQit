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

import numbers
import warnings
import queue
from typing import Iterable, List

import numpy as np
import scipy.sparse.linalg
from scipy import sparse

from spinqit.model.parameter import LazyParameter


def schmidt_decompose(psi,
                      sys_A=None,
                      return_singular_vector=True,
                      return_rank=True):
    r"""Calculate the Schmidt decomposition of a quantum state :math:`\lvert\psi\rangle=\sum_ic_i\lvert i_A\rangle\otimes\lvert i_B \rangle`.

    Args:
        psi: State vector form of the quantum state, with shape (2**n)
        sys_A: Qubit indices to be included in subsystem A (other qubits are included in subsystem B), default are the first half qubits of :math:`\lvert \psi\rangle`

    Returns:
        contains elements

        * A one dimensional array composed of Schmidt coefficients, with shape ``(k)``
        * A high dimensional array composed of bases for subsystem A :math:`\lvert i_A\rangle`, with shape ``(k, 2**m, 1)``
        * A high dimensional array composed of bases for subsystem B :math:`\lvert i_B\rangle` , with shape ``(k, 2**m, 1)``
    """
    assert psi.ndim == 1, 'Psi must be a one dimensional vector.'
    assert np.log2(psi.size).is_integer(), 'The number of amplitutes must be an integral power of 2.'

    tot_qu = int(np.log2(psi.size))
    sys_A = sys_A if sys_A is not None else [i for i in range(tot_qu // 2)]
    sys_B = [i for i in range(tot_qu) if i not in sys_A]

    # Permute qubit indices
    psi = psi.reshape([2] * tot_qu).transpose(sys_A + sys_B)

    # construct amplitude matrix
    amp_mtr = psi.reshape([2 ** len(sys_A), 2 ** len(sys_B)])

    # Standard process to obtain schmidt decomposition
    u, c, v = sparse.linalg.svds(amp_mtr, k=3)

    k = np.count_nonzero(c > 1e-13)
    c = (c[:k])
    u = (u.T[:k].reshape([k, -1, 1]))
    v = (v[:k].reshape([k, -1, 1]))
    return c, u, v


def get_ground_state_info(H):
    # 计算 H 的特征值与特征向量
    vals, vecs = sparse.linalg.eigsh(H, k=1, which='SM')  # 'buckling' | 'cayley'
    # 获取基态
    ground_state = (vecs[:, 0])
    print(ground_state)
    # 获取基态能量
    ground_state_energy = vals[0]
    print(f'The ground state energy is {ground_state_energy:.5f} Ha.')
    # 对基态运用施密特分解
    l, _, _ = schmidt_decompose(ground_state)
    print(f'Schmidt rank of the ground state is {l.shape[0]}.')
    return ground_state_energy


def is_diagonal(mat: np.ndarray) -> bool:
    """
    Check whether a matrix is a diagonal matrix or not
    """

    def nodiag_view(a):
        m = a.shape[0]
        p, q = a.strides
        return np.lib.stride_tricks.as_strided(a[:, 1:], (m - 1, m), (p + q, q))

    return (nodiag_view(mat) == 0).all()


def calculate_phase(mat1, mat2):
    """
    Calculate the phase difference between two matrix
    """
    #
    if isinstance(mat1, list):
        mat1 = np.array(mat1)
    if len(mat1.shape) != 1 and is_diagonal(mat1):
        mat1 = np.diagonal(mat1),
    if len(mat2.shape) != 1 and is_diagonal(mat2):
        mat2 = np.diagonal(mat2)

    if len(mat1.shape) == 1 and len(mat2.shape) == 1:
        global_phase_matrix = mat1 * mat2.conj()
    else:
        global_phase_matrix = np.diagonal(mat1 @ mat2.T.conj())
    global_phase = np.log(global_phase_matrix[0]) / 1j
    eq_id = np.allclose(global_phase_matrix / global_phase_matrix[0], np.ones(global_phase_matrix.shape[0]))

    if eq_id:
        return global_phase

    warnings.warn('There are no global phase between mat1 and mat2')
    return None


def _flatten(x):
    if isinstance(x, LazyParameter):
        yield x
    elif isinstance(x, np.ndarray):
        yield from _flatten(x.flat)
    elif isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
        try:
            for item in x:
                yield from _flatten(item)
        except TypeError:
            yield x
    else:
        yield x


def _unflatten(flat, model):
    if isinstance(model, (numbers.Number, str)):
        return flat[0], flat[1:]

    if isinstance(model, np.ndarray):
        idx = model.size
        res = np.array(flat)[:idx].reshape(model.shape)
        return res, flat[idx:]

    if isinstance(model, Iterable):
        res = []
        for x in model:
            val, flat = _unflatten(flat, x)
            res.append(val)
        return res, flat

    raise TypeError("Unsupported type in the model: {}".format(type(model)))


def unflatten(flat, model):
    # pylint:disable=len-as-condition
    res, tail = _unflatten(np.asarray(flat), model)
    if len(tail) != 0:
        raise ValueError("Flattened iterable has more elements than the model.")
    return res


def _topological_sort(graph) -> List[int]:
    indegree_table = [0] * graph.vcount()
    for i in range(graph.vcount()):
        indegree_table[i] = graph.vs[i].indegree()
    registers = graph.vs.select(type=4)
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


def to_list(*x):
    return list(_flatten(x))


def _dfs(root_index: int, graph, visited, result: List):
    successors = graph.neighbors(root_index, mode='out')
    for s in successors:
        if s not in visited:
            _dfs(s, graph, visited, result)
    result.append(root_index)
    visited.add(root_index)


def get_interface(tensor):
    """Returns the name of the package that any array/tensor manipulations
    will dispatch to.

    Args:
        tensor (tensor_like): tensor input

    Returns:
        str: name of the interface
    """
    import autoray as ar
    namespace = tensor.__class__.__module__.split(".")[0]

    if namespace in ("spinqit", "autograd"):
        return "spinq"

    res = ar.infer_backend(tensor)

    if res == "builtins":
        return "numpy"

    return res


def requires_grad(params):
    interface = get_interface(params)
    if interface == "tensorflow":
        return getattr(params, "trainable", False)
        # import tensorflow as tf

        # try:
        #     from tensorflow.python.eager.tape import should_record_backprop
        # except ImportError:  # pragma: no cover
        #     from tensorflow.python.eager.tape import should_record as should_record_backprop

        # return should_record_backprop([tf.convert_to_tensor(params)])

    if interface == "spinq":
        return getattr(params, "trainable", False)

    if interface == "torch":
        return getattr(params, "requires_grad", False)

    if interface == "paddle":
        return not getattr(params, "stop_gradient", True)

    if interface == "jax":
        import jax

        return isinstance(params, jax.core.Tracer)
    return False
