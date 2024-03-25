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
from autoray import numpy as ar


class Fidelity:
    """
    This class only supports state fidelity calculate, especially two pure state, i.e., 1-D state vector quantum state,
    The mixed state(density matrix) or gate fidelity is not supported for now, will be added in the future

    The Fidelity support multi data type, torch.Tensor, tf.Variable, Paddle.Tensor, spinqit.Parameter. and support the
    autograd differentiation.

    Example:
        state0 = [0.98753537 - 0.14925137j, 0.00746879 - 0.04941796j]
        state1 = [0.99500417 + 0.j, 0.09983342 + 0.j]
        fidelity_fn = Fidelity()
        print(fidelity_fn(state0, state1))
        # 0.9905158182231922

    Example2:
        state0 = torch.tensor([0.98753537 - 0.14925137j, 0.00746879 - 0.04941796j])
        state1 = torch.tensor([0.99500417 + 0.j, 0.09983342 + 0.j])
        fidelity_fn = Fidelity()
        print(fidelity_fn(state0, state1))
        # 0.9905158182231922

    Example3
        state0 = torch.tensor([0.98753537 - 0.14925137j, 0.00746879 - 0.04941796j], requires_grad=True)
        state1 = torch.tensor([0.99500417 + 0.j, 0.09983342 + 0.j])
        fidelity_fn = Fidelity()
        res = fidelity_fn(state0, state1)
        res.backward() # get the gradients of state0
        print(state0.grad)
        # tensor([1.9569-0.3053j, 0.1963-0.0306j])

    """

    def __init__(self):
        pass

    def __call__(self, state, target_state):
        return ar.abs(ar.matmul(ar.conj(target_state), state)) ** 2


def _density_matrix_from_state(state, indices):
    len_state = state.shape[0]

    # Get dimension of the quantum system and reshape
    num_indices = int(ar.log2(len_state))
    consecutive_wires = list(range(num_indices))
    state = ar.reshape(state, [2] * num_indices)

    # Get the system to be traced
    traced_system = [x for x in consecutive_wires if x not in indices]

    # Return the reduced density matrix by using numpy tensor product
    density_matrix = ar.tensordot(state, ar.conj(state), (traced_system, traced_system))
    density_matrix = ar.reshape(density_matrix, (2 ** len(indices), 2 ** len(indices)))

    return density_matrix


def _compute_vn_entropy(density_matrix, div_base):
    evs = (ar.linalg.eigvalsh(density_matrix))
    evs = ar.where(evs > 0, evs, 1.0)
    entropy = -ar.sum(ar.abs(evs)*ar.log(ar.abs(evs))) / div_base

    return entropy


def vn_entropy(state, indices, base):
    density_matrix = _density_matrix_from_state(state, indices)
    return _compute_vn_entropy(density_matrix, base)


class VNEntropy:
    """
    The VNEntropy support multi data type, torch.Tensor, tf.Variable, Paddle.Tensor, spinqit.Parameter. and support the
    autograd differentiation.

    Example:
        from spinqit.loss.quantum_loss import VNEntropy
        from spinqit.model.parameter import Parameter


        vn_entropy_fn = VNEntropy()
        x = Parameter([1, 0, 0, 1]) / ar.sqrt(2)
        vn_entropy = vn_entropy_fn(x, indices=[0])
        print(vn_entropy)
        # 0.6931471805599454

        vn_entropy_fn = VNEntropy(log_base=2)
        vn_entropy = vn_entropy_fn(x, indices=[0])
        print(vn_entropy)
        # 1.0


    """

    def __init__(self, log_base=None):
        if log_base:
            div_base = ar.log(log_base)
        else:
            div_base = 1
        self.div_base = div_base

    def __call__(self, state, indices):
        return vn_entropy(state, indices, self.div_base)


def _compute_mutual_info(
        state, indices0, indices1, base=None
):
    """Compute the mutual information between the subsystems."""
    all_indices = sorted([*indices0, *indices1])
    vn_entropy_1 = vn_entropy(
        state, indices=indices0, base=base
    )
    vn_entropy_2 = vn_entropy(
        state, indices=indices1, base=base
    )
    vn_entropy_12 = vn_entropy(
        state, indices=all_indices, base=base
    )

    return vn_entropy_1 + vn_entropy_2 - vn_entropy_12


class MutualInfo:
    def __init__(self, log_base=None):
        if log_base:
            div_base = ar.log(log_base)
        else:
            div_base = 1
        self.div_base = div_base

    def __call__(self, state, indices0, indices1):
        if len([index for index in indices0 if index in indices1]) > 0:
            raise ValueError("Subsystems for computing mutual information must not overlap.")

        # Cast to a complex array
        state = ar.astype(state, 'complex64')

        state_shape = state.shape
        if len(state_shape) > 0:
            len_state = state_shape[0]
            if state_shape in [(len_state,), (len_state, len_state)]:
                return _compute_mutual_info(
                    state, indices0, indices1, base=self.div_base,
                )

        raise ValueError("The state is not a state vector or a density matrix.")


def _compute_relative_entropy(rho, sigma, base=None):
    r"""
    Compute the quantum relative entropy of density matrix rho with respect to sigma.

    .. math::
        S(\rho\,\|\,\sigma)=-\text{Tr}(\rho\log\sigma)-S(\rho)=\text{Tr}(\rho\log\rho)-\text{Tr}(\rho\log\sigma)
        =\text{Tr}(\rho(\log\rho-\log\sigma))

    where :math:`S` is the von Neumann entropy.
    """
    if base:
        div_base = ar.log(base)
    else:
        div_base = 1

    evs_rho, u_rho = ar.linalg.eigh(rho)
    evs_sig, u_sig = ar.linalg.eigh(sigma)

    # cast all eigenvalues to real
    evs_rho, evs_sig = ar.real(evs_rho), ar.real(evs_sig)

    # zero eigenvalues need to be treated very carefully here
    # we use the convention that 0 * log(0) = 0
    evs_sig = ar.where(evs_sig == 0, 0.0, evs_sig)
    rho_nonzero_mask = ar.where(evs_rho == 0.0, False, True)

    evs = ar.where(rho_nonzero_mask, evs_rho, 1.0)
    ent = -ar.sum(ar.abs(evs)*ar.log(ar.abs(evs)))

    # the matrix of inner products between eigenvectors of rho and eigenvectors
    # of sigma; this is a doubly stochastic matrix
    rel = ar.abs(ar.transpose(ar.conj(u_rho))@u_sig) ** 2

    rel = ar.sum(ar.where(rel == 0.0, 0.0, ar.log(evs_sig) * rel), axis=1)
    rel = -ar.sum(ar.where(rho_nonzero_mask, evs_rho * rel, 0.0))

    return (rel - ent) / div_base


class RelativeEntropy:
    """
    Compute the quantum relative entropy of one state with respect to another.
    """

    def __init__(self, div_base=None):
        self.div_base = div_base

    def __call__(self, state0, state1):
        len_state0 = state0.shape[0]

        len_state1 = state1.shape[0]

        # Get dimension of the quantum system and reshape
        num_indices0 = int(ar.log2(len_state0))
        num_indices1 = int(ar.log2(len_state1))

        if num_indices0 != num_indices1:
            raise ValueError("The two states must have the same number of wires.")

        if state0.shape == (len_state0,):
            state0 = ar.outer(state0, ar.conj(state0))

        if state1.shape == (len_state1,):
            state1 = ar.outer(state1, ar.conj(state1))

        return _compute_relative_entropy(state0, state1, base=self.div_base)
