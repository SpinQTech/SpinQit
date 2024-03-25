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
import numpy as np

from spinqit import Circuit, CX, H, Ry, X, Rx, Rz, Parameter, generate_hamiltonian_matrix
from spinqit.interface.qlayer import QLayer
from spinqit.grad import qgrad
from .loss import expval

OBS_MAP = {"PauliX": "X", "PauliY": "Y", "PauliZ": "Z", "Hadamard": "H", "Identity": "I"}
bohr_angs = 0.529177210903


def _openfermion_to_spinq(qubit_operator, qubits_num=None):
    r"""Convert OpenFermion ``QubitOperator`` to a 2-tuple of coefficients and Pauli String.

    Args:
        qubit_operator (QubitOperator): fermionic-to-qubit transformed operator in terms of
            Pauli matrices
        qubits_num (int): The number of qubits for hamiltonian, default to None,

    Returns:
        List[Tuple(string, float)]: The list of hamiltonian string with coeff
    """
    if qubits_num is None:
        n_qubits = (
            1 + max([max([i for i, _ in t]) if t else 1 for t in qubit_operator.terms])
            if qubit_operator.terms
            else 1
        )
    else:
        n_qubits = qubits_num

    if not qubit_operator.terms:  
        return [('I' * n_qubits, 0)]

    ham = []
    for term, coef in qubit_operator.terms.items():
        origin = ['I'] * n_qubits
        for site, pstr in term:
            origin[site] = pstr
        ham.append((''.join(origin), coef.real))
    return ham


def _basis_state(circ: Circuit, state):
    for idx, s in enumerate(state):
        if s == 1:
            circ << (X, [idx])


def _double_excitation(circ: Circuit, qubits, params):
    circ << (CX, [qubits[2], qubits[3]])
    circ << (CX, [qubits[0], qubits[2]])
    circ << (H, qubits[3])
    circ << (H, qubits[0])
    circ << (CX, [qubits[2], qubits[3]])
    circ << (CX, [qubits[0], qubits[1]])
    circ << (Ry, qubits[1], params / 8)
    circ << (Ry, qubits[0], -params / 8)
    circ << (CX, [qubits[0], qubits[3]])
    circ << (H, [qubits[3]])
    circ << (CX, [qubits[3], qubits[1]])
    circ << (Ry, qubits[1], params / 8)
    circ << (Ry, qubits[0], -params / 8)
    circ << (CX, [qubits[2], qubits[1]])
    circ << (CX, [qubits[2], qubits[0]])
    circ << (Ry, qubits[1], -params / 8)
    circ << (Ry, qubits[0], params / 8)
    circ << (CX, [qubits[3], qubits[1]])
    circ << (H, [qubits[3]])
    circ << (CX, [qubits[0], qubits[3]])
    circ << (Ry, qubits[1], -params / 8)
    circ << (Ry, qubits[0], params / 8)
    circ << (CX, [qubits[0], qubits[1]])
    circ << (CX, [qubits[2], qubits[0]])
    circ << (H, qubits[0])
    circ << (H, qubits[3])
    circ << (CX, [qubits[0], qubits[2]])
    circ << (CX, [qubits[2], qubits[3]])


def _single_excitation(circuit, s_wires, params):
    circuit << (CX, [s_wires[0], s_wires[1]])
    circuit << (Ry, s_wires[0], params / 2)
    circuit << (CX, [s_wires[1], s_wires[0]])
    circuit << (Ry, s_wires[0], -params / 2)
    circuit << (CX, [s_wires[1], s_wires[0]])
    circuit << (CX, [s_wires[0], s_wires[1]])


def _excitations(electrons, orbitals, delta_sz=0):
    r"""Generate single and double excitations from a Hartree-Fock reference state.
    """

    if not electrons > 0:
        raise ValueError(
            f"The number of active electrons has to be greater than 0 \n"
            f"Got n_electrons = {electrons}"
        )

    if orbitals <= electrons:
        raise ValueError(
            f"The number of active spin-orbitals ({orbitals}) "
            f"has to be greater than the number of active electrons ({electrons})."
        )

    if delta_sz not in (0, 1, -1, 2, -2):
        raise ValueError(
            f"Expected values for 'delta_sz' are 0, +/- 1 and +/- 2 but got ({delta_sz})."
        )

    # define the spin projection 'sz' of the single-particle states
    sz = np.array([0.5 if (i % 2 == 0) else -0.5 for i in range(orbitals)])

    singles = [
        [r, p]
        for r in range(electrons)
        for p in range(electrons, orbitals)
        if sz[p] - sz[r] == delta_sz
    ]

    doubles = [
        [s, r, q, p]
        for s in range(electrons - 1)
        for r in range(s + 1, electrons)
        for q in range(electrons, orbitals - 1)
        for p in range(q + 1, orbitals)
        if (sz[p] + sz[q] - sz[r] - sz[s]) == delta_sz
    ]

    return singles, doubles


def _hf_state(electrons, orbitals):
    r"""Generate the occupation-number vector representing the Hartree-Fock state.
    """

    if electrons <= 0:
        raise ValueError(
            f"The number of active electrons has to be larger than zero; "
            f"got 'electrons' = {electrons}"
        )

    if electrons > orbitals:
        raise ValueError(
            f"The number of active orbitals cannot be smaller than the number of active electrons;"
            f" got 'orbitals'={orbitals} < 'electrons'={electrons}"
        )

    state = np.where(np.arange(orbitals) < electrons, 1, 0)

    return np.array(state)


def scf_calculate(coordinates,
                  symbols,
                  basis,
                  multiplicity,
                  charge):
    from openfermionpyscf import run_pyscf
    import openfermion

    geometry = [
        [symbol, tuple(np.array(coordinates)[3 * i: 3 * i + 3] * bohr_angs)]
        for i, symbol in enumerate(symbols)
    ]

    molecule = run_pyscf(openfermion.MolecularData(geometry, basis, multiplicity, charge), run_scf=1, verbose=0)

    terms_molecular_hamiltonian = molecule.get_molecular_hamiltonian()

    fermionic_hamiltonian = openfermion.transforms.get_fermion_operator(terms_molecular_hamiltonian)
    ham = openfermion.transforms.jordan_wigner(fermionic_hamiltonian)

    qubits = molecule.n_qubits
    electrons = molecule.n_electrons
    hamiltonian = _openfermion_to_spinq(ham)
    return electrons, hamiltonian, qubits


def construct_givens_circuit(qubits, electrons, delta_sz_list=None):
    singles, doubles = get_givens_single_double(electrons,qubits,delta_sz_list)
    state = _hf_state(electrons, qubits)
    qubit_num = qubits
    circ = Circuit()
    circ.allocateQubits(qubit_num)
    params = circ.add_params(shape=len(singles) + len(doubles)) #, argnum=0)
    circ = Givens(circ, singles, doubles, state, params[:len(singles)], params[len(singles):])
    return circ, Parameter(np.zeros(shape=len(singles) + len(doubles)))


def Givens(circ, singles, doubles, hf_state, single_params, double_params):
    _basis_state(circ, hf_state)
    for i, d in enumerate(doubles):
        _double_excitation(circ, d, double_params[i])
    for j, s in enumerate(singles):
        _single_excitation(circ, s, single_params[j])
    return circ


def excitations_to_uccsd(singles, doubles, qubit_num=None):
    r"""Map the single and double excitations obtained from the 'excitations' function to the qubits where the UCCSD circuit will act.

    qubit_num: The number of qubits in the circuit 
    """

    # Obtain the index of the qubit that is affected the most by single and double excitation gates, in order to determine the number of qubits in the circuit
    max_idx = 0
    if singles:
        max_idx = np.max(singles)
    if doubles:
        max_idx = max(np.max(doubles), max_idx)

    if qubit_num is None:
        qubit_list = range(max_idx + 1)
    else:
        qubit_list = range(qubit_num)

    uccsd_single_list = []
    for r, p in singles:
        s_list = [qubit_list[i] for i in range(r, p + 1)]
        uccsd_single_list.append(s_list)

    uccsd_double_list = []
    for s, r, q, p in doubles:
        d1_list = [qubit_list[i] for i in range(s, r + 1)]
        d2_list = [qubit_list[i] for i in range(q, p + 1)]
        uccsd_double_list.append([d1_list, d2_list])

    return uccsd_single_list, uccsd_double_list


def single_layer(circ: Circuit, r, p, params, set_cnot_idx: list):
    r"""
    circ: the input circuit
    r: qubit occupying the orbital
    p: qubit not occupying the orbital
    param_idx (int): parameter index
    set_cnot_idx (list): qubits for CNOT
    """

    # exp(YX) circuit

    # first layer
    # YX，from left to right, acts on the quantum bits s, r, q, p respectively. It is necessary to use H or Rx gates to convert Z basis to X or Y basis
    circ << (Rx, r, [-np.pi / 2])
    circ << (H, p)

    # second layer， CNOT
    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    # thrid layer， Rz
    circ << (Rz, p, params / 2)

    # fourth layer, CNOT
    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    # fifth layer，dagger of the first layer
    circ << (Rx, r, [np.pi / 2])
    circ << (H, p)

    # exp(XY) circuit

    circ << (H, r)
    circ << (Rx, p, [-np.pi / 2])

    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    circ << (Rz, p, -params / 2)

    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    circ << (H, r)
    circ << (Rx, p, [np.pi / 2])


def uccsd_single_excitation(circ: Circuit, qubits_list: list, params):
    r"""
    single excitation gates in uccsd
    Refer to `Quantum algorithms for electronic structure calculations: particle/hole Hamiltonian and optimized wavefunction expansions`
    """
    r = qubits_list[0]
    p = qubits_list[-1]

    set_cnot_idx = [qubits_list[l: l + 2] for l in range(len(qubits_list) - 1)]
    single_layer(circ, r, p, params, set_cnot_idx)


def uccsd_double_excitation(circ: Circuit, qubits_1: list, qubits_2: list, params):
    s = qubits_1[0]
    r = qubits_1[-1]
    q = qubits_2[0]
    p = qubits_2[-1]

    cnots_idx_1 = [qubits_1[l: l + 2] for l in range(len(qubits_1) - 1)]
    cnots_idx_2 = [qubits_2[l: l + 2] for l in range(len(qubits_2) - 1)]

    set_cnot_idx = cnots_idx_1 + [[r, q]] + cnots_idx_2
    double_layer(circ, s, r, q, p, params, set_cnot_idx)


def double_layer(circ: Circuit, s, r, q, p, params, set_cnot_idx: list):
    r"""

    circ: Circuit to update
    s,r: qubits occupying the orbital
    q,p: qubits not occupying the orbital
    param_idx (int): parameter index, used to control the initial parameters of the double excitation gates
    set_cnot_idx (list): qubits for CNOT
    """

    # exp(XXYX) circuit
    # first layer
    # XXYX, from left to right, acts on the qubits s, r, q, p respectively. It is necessary to use H or Rx gates to convert Z basis to X or Y basis.
    circ << (H, s)
    circ << (H, r)
    circ << (Rx, q, [-np.pi / 2])
    circ << (H, p)

    # second layer, CNOT
    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    # third layer, Rz
    circ << (Rz, p, params / 8)

    # fourth layer, CNOT
    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    # fifth layer，dagger of the first layer
    circ << (H, p)
    circ << (Rx, q, [np.pi / 2])
    circ << (H, r)
    circ << (H, s)

    # YXYY
    circ << (Rx, s, [-np.pi / 2])
    circ << (H, r)
    circ << (Rx, q, [-np.pi / 2])
    circ << (Rx, p, [-np.pi / 2])

    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    circ << (Rz, p, params / 8)

    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    circ << (Rx, p, [np.pi / 2])
    circ << (Rx, q, [np.pi / 2])
    circ << (H, r)
    circ << (Rx, s, [np.pi / 2])

    # XYYY
    circ << (H, s)
    circ << (Rx, r, [-np.pi / 2])
    circ << (Rx, q, [-np.pi / 2])
    circ << (Rx, p, [-np.pi / 2])

    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    circ << (Rz, p, params / 8)

    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    circ << (Rx, p, [np.pi / 2])
    circ << (Rx, q, [np.pi / 2])
    circ << (Rx, r, [np.pi / 2])
    circ << (H, s)

    # XXXY
    circ << (H, s)
    circ << (H, r)
    circ << (H, q)
    circ << (Rx, p, [-np.pi / 2])

    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    circ << (Rz, p, params / 8)

    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    circ << (Rx, p, [np.pi / 2])
    circ << (H, q)
    circ << (H, r)
    circ << (H, s)

    # YXXX
    circ << (Rx, s, [-np.pi / 2])
    circ << (H, r)
    circ << (H, q)
    circ << (H, p)

    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    circ << (Rz, p, -params / 8)

    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    circ << (H, p)
    circ << (H, q)
    circ << (H, r)
    circ << (Rx, s, [np.pi / 2])

    # XYXX
    circ << (H, s)
    circ << (Rx, r, [-np.pi / 2])
    circ << (H, q)
    circ << (H, p)

    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    circ << (Rz, p, -params / 8)

    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    circ << (H, p)
    circ << (H, q)
    circ << (Rx, r, [np.pi / 2])
    circ << (H, s)

    # YYYX
    circ << (Rx, s, [-np.pi / 2])
    circ << (Rx, r, [-np.pi / 2])
    circ << (Rx, q, [-np.pi / 2])
    circ << (H, p)

    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    circ << (Rz, p, -params / 8)

    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    circ << (H, p)
    circ << (Rx, q, [np.pi / 2])
    circ << (Rx, r, [np.pi / 2])
    circ << (Rx, s, [np.pi / 2])

    # YYXY
    circ << (Rx, s, [-np.pi / 2])
    circ << (Rx, r, [-np.pi / 2])
    circ << (H, q)
    circ << (Rx, p, [-np.pi / 2])

    for cnot_dix in set_cnot_idx:
        circ << (CX, cnot_dix)

    circ << (Rz, p, -params / 8)

    for cnot_dix in reversed(set_cnot_idx):
        circ << (CX, cnot_dix)

    circ << (Rx, p, [np.pi / 2])
    circ << (H, q)
    circ << (Rx, r, [np.pi / 2])
    circ << (Rx, s, [np.pi / 2])


def construct_uccsd_circuit(qubits, electrons, delta_sz_list=None):
    if delta_sz_list is None:
        delta_sz_list = [0]
    singles_list = []
    doubles_list = []
    for delta_sz in delta_sz_list:
        singles, doubles = _excitations(electrons, qubits, delta_sz=delta_sz)

        # list of qubits subjected to the action of single and double excitation gates
        singles_list += singles
        doubles_list += doubles

    uccsd_single_list, uccsd_double_list = excitations_to_uccsd(singles_list, doubles_list, qubit_num=qubits)

    cir = Circuit()
    cir.allocateQubits(qubits)
    params = cir.add_params(shape=(len(uccsd_double_list) + len(uccsd_single_list)))
    hf_state = _hf_state(electrons, qubits)
    _basis_state(circ=cir, state=hf_state)

    for i, (qubits_1, qubits_2) in enumerate(uccsd_double_list):
        uccsd_double_excitation(cir, qubits_1, qubits_2, params[i])

    for j, qubits_list in enumerate(uccsd_single_list):
        uccsd_single_excitation(cir, qubits_list, params[j + len(uccsd_double_list)])
    params = Parameter(np.zeros(shape=len(uccsd_double_list) + len(uccsd_single_list)))

    return cir, params


def generalized_singles(qubits, delta_sz):
    sz = np.array(
        [0.5 if (i % 2 == 0) else -0.5 for i in range(qubits)]
    )

    gen_singles_list = []
    qubits_list = list(range(qubits))
    for r in range(qubits):
        for p in range(qubits):
            if sz[p] - sz[r] == delta_sz and p != r:
                if r < p:
                    gen_singles_list.append(qubits_list[r: p + 1])
                else:
                    gen_singles_list.append(qubits_list[p: r + 1][::-1])

    return gen_singles_list


def generalized_pair_doubles(qubits):
    pair_gen_doubles_list = []

    qubits_list = list(range(qubits))
    for r in range(0, qubits - 1, 2):
        for p in range(0, qubits - 1, 2):
            if p != r:
                pair_gen_doubles_list.append([qubits_list[r: r + 2], qubits_list[p: p + 2]])

    return pair_gen_doubles_list


def construct_kupccgsd_circuit(qubits, electrons, delta_sz_list=None, k=1):
    if delta_sz_list is None:
        delta_sz_list = [0]
    gen_singles_list = [] 

    for delta_sz in delta_sz_list:
        gen_singles_list += generalized_singles(qubits=qubits, delta_sz=delta_sz)

    pair_gen_doubles_list = generalized_pair_doubles(qubits=qubits)

    cir = Circuit()
    cir.allocateQubits(qubits)
    params = cir.add_params(shape=(k * (len(pair_gen_doubles_list) + len(gen_singles_list)))) #, argnum=0)
    hf_state = _hf_state(electrons, qubits)
    _basis_state(circ=cir, state=hf_state)

    for depth in range(k):
        now_idx = depth * (len(pair_gen_doubles_list) + len(gen_singles_list))

        if pair_gen_doubles_list is not None:
            for i, (qubits_1, qubits_2) in enumerate(pair_gen_doubles_list):
                uccsd_double_excitation(cir, qubits_1, qubits_2, params[i + now_idx])

        if gen_singles_list is not None:
            for j, qubits_list in enumerate(gen_singles_list):
                uccsd_single_excitation(cir, qubits_list, params[j + len(pair_gen_doubles_list) + now_idx])
    params = Parameter(np.zeros(shape=(k * (len(pair_gen_doubles_list) + len(gen_singles_list)))))
    return cir, params


def qucc_single_excitation(circ: Circuit, qubits_list: list, params):
    r = qubits_list[0]
    p = qubits_list[-1]

    circ << (Rz, r, np.pi / 2)
    circ << (Ry, p, -np.pi / 2)
    circ << (Rz, p, -np.pi / 2)

    circ << (CX, qubits_list)

    circ << (Ry, r, params / 2)
    circ << (Rz, p, -np.pi / 2)

    circ << (CX, qubits_list)

    circ << (Ry, r, -params / 2)
    circ << (H, p)

    circ << (CX, qubits_list)


def qucc_double_excitation(circ: Circuit, qubits: list, params):
    s = qubits[0]
    r = qubits[1]
    q = qubits[2]
    p = qubits[3]

    circ << (CX, [s, r])
    circ << (CX, [q, p])
    circ << (X, r)
    circ << (X, p)
    circ << (CX, [s, q])

    circ << (Ry, s, params / 8)
    circ << (H, r)
    circ << (CX, [s, r])

    circ << (Ry, s, -params / 8)
    circ << (H, p)
    circ << (CX, [s, p])

    circ << (Ry, s, params / 8)
    circ << (CX, [s, r])

    circ << (Ry, s, -params / 8)
    circ << (H, q)
    circ << (CX, [s, q])

    circ << (Ry, s, params / 8)
    circ << (CX, [s, r])

    circ << (Ry, s, -params / 8)
    circ << (CX, [s, p])

    circ << (Ry, s, params / 8)
    circ << (H, p)
    circ << (CX, [s, r])

    circ << (Ry, s, -params / 8)
    circ << (H, r)
    circ << (Rz, q, -np.pi / 2)
    circ << (CX, [s, q])

    circ << (Rz, s, np.pi / 2)
    circ << (Rz, q, -np.pi / 2)

    circ << (X, r)
    circ << (Ry, q, -np.pi / 2)
    circ << (X, p)

    circ << (CX, [s, r])
    circ << (CX, [q, p])


def construct_qucc_circuit(qubits, electrons, delta_sz_list=None, k=1):
    if delta_sz_list is None:
        delta_sz_list = [0]
    qucc_single_list = [] 
    qucc_double_list = []

    for delta_sz in delta_sz_list:
        singles, doubles = _excitations(electrons, qubits, delta_sz=delta_sz)
        qucc_single_list += singles
        qucc_double_list += doubles

    cir = Circuit()
    cir.allocateQubits(qubits)
    params = cir.add_params(shape=(k * (len(qucc_double_list) + len(qucc_single_list)))) 
    hf_state = _hf_state(electrons, qubits)
    _basis_state(circ=cir, state=hf_state)

    for d in range(k):
        for i, qubits_list in enumerate(qucc_double_list):
            qucc_double_excitation(cir, qubits_list, params[d * (len(qucc_double_list) + len(qucc_single_list)) + i])
        for j, qubits_list in enumerate(qucc_single_list):
            qucc_single_excitation(cir, qubits_list, params[
                d * (len(qucc_double_list) + len(qucc_single_list)) + (j + len(qucc_double_list))])
    params = Parameter(np.zeros(shape=(k * (len(qucc_double_list) + len(qucc_single_list)))))
    return cir, params


def double_circuit(doubles_select, hf_state, qubit_num):
    circ = Circuit()
    circ.allocateQubits(qubit_num)
    params = circ.add_params(shape=len(doubles_select))
    _basis_state(circ, hf_state)
    for i, excitation in enumerate(doubles_select):
        _double_excitation(circ, excitation, params[i])
    return circ


def double_grad(doubles_select, hf_state, ham, qubits):
    circ = double_circuit(doubles_select, hf_state, qubits)
    params = Parameter([0.] * len(doubles_select))
    qlayer = QLayer(circ,  backend_mode='torch', measure=expval(ham), grad_method='backprop')
    grads = qgrad(qlayer)(params)
    return grads[0]


def get_double_params(doubles, state, ham, qubit_num):
    circ = Circuit()
    circ.allocateQubits(qubit_num)
    params = circ.add_params(shape=len(doubles))
    circ = Givens(circ, [], doubles, state, [], params)
    double_qlayer = QLayer(circ, backend_mode='torch', measure=expval(ham), grad_method='backprop')

    doubles_params = Parameter(np.zeros(len(doubles)))
    for _ in range(20):
        doubles_params -= 0.5 * qgrad(double_qlayer)(doubles_params)[0]
    return doubles_params


def single_circuit(single_select, double_select, double_params, hf_state, qubit_num):
    circ = Circuit()
    circ.allocateQubits(qubit_num)
    params = circ.add_params(shape=len(single_select)) 
    circ = Givens(circ, single_select, double_select, hf_state, params, double_params)
    return circ


def single_grad(single_select, double_select, double_params, hf_state, ham, qubit_num):
    circ = single_circuit(single_select, double_select, double_params, hf_state, qubit_num)
    qlayer = QLayer(circ,  backend_mode='torch', measure=expval(ham), grad_method='backprop')
    params = Parameter(np.zeros(len(single_select)))
    grads = qgrad(qlayer)(params)
    return grads[0]


def get_givens_single_double(electrons, qubits, delta_sz_list):
    if delta_sz_list is None:
        delta_sz_list = [0]
    singles_list = []
    doubles_list = []
    for delta_sz in delta_sz_list:
        singles, doubles = _excitations(electrons, qubits, delta_sz=delta_sz)
        singles_list += singles
        doubles_list += doubles
    return singles_list, doubles_list


def construct_adapt_circuit(qubits, electrons, ham, delta_sz_list=None):
    singles_list, doubles_list = get_givens_single_double(electrons, qubits, delta_sz_list)
    state = _hf_state(electrons, qubits)

    doubles_grad = double_grad(doubles_list, state, ham, qubits)
    doubles = [doubles_list[i] for i in range(len(doubles_list)) if abs(doubles_grad[i]) > 1.0e-5]
    doubles_params = get_double_params(doubles, state, ham, qubits)

    singles_grad = single_grad(singles_list, doubles, doubles_params, state, ham, qubits)
    singles = [singles_list[i] for i in range(len(singles_list)) if abs(singles_grad[i]) > 1.0e-5]

    qubit_num = qubits
    circ = Circuit()
    circ.allocateQubits(qubit_num)
    params = circ.add_params(shape=len(singles) + len(doubles)) 
    circ = Givens(circ, singles, doubles, state, params[:len(singles)], params[len(singles):])
    return circ, Parameter(np.zeros(shape=len(singles) + len(doubles)))

