import numpy as np

from spinqit import Circuit, CX, H, Ry, X
from spinqit.model.parameter import Parameter

OBS_MAP = {"PauliX": "X", "PauliY": "Y", "PauliZ": "Z", "Hadamard": "H", "Identity": "I"}
bohr_angs = 0.529177210903


def _openfermion_to_spinq(qubit_operator, qubits=None):
    r"""Convert OpenFermion ``QubitOperator`` to a 2-tuple of coefficients and Pauli String.

    Args:
        qubit_operator (QubitOperator): fermionic-to-qubit transformed operator in terms of
            Pauli matrices
        qubits (list, tuple): The qubits for hamiltonian

    Returns:
        List[Tuple(int, string)]: The list of hamiltonian string with coeff
    """
    n_qubits = (
        1 + max([max([i for i, _ in t]) if t else 1 for t in qubit_operator.terms])
        if qubit_operator.terms
        else 1
    )

    if not qubit_operator.terms:  # added since can't unpack empty zip to (coeffs, ops) below
        return [('I' * n_qubits, 0)]

    ham = []
    for term, coef in qubit_operator.terms.items():
        origin = ['I'] * n_qubits
        for site, pstr in term:
            origin[site] = pstr
        ham.append((''.join(origin), coef))
    return ham


def _basis_state(circ: Circuit, state):
    for idx, s in enumerate(state):
        if s == 1:
            circ << (X, [idx])


def _double_excitation(circ: Circuit, qubits):
    circ << (CX, [qubits[2], qubits[3]])
    circ << (CX, [qubits[0], qubits[2]])
    circ << (H, qubits[3])
    circ << (H, qubits[0])
    circ << (CX, [qubits[2], qubits[3]])
    circ << (CX, [qubits[0], qubits[1]])
    circ << (Ry, qubits[1], lambda x: x[0] / 8)
    circ << (Ry, qubits[0], lambda x: -x[0] / 8)
    circ << (CX, [qubits[0], qubits[3]])
    circ << (H, [qubits[3]])
    circ << (CX, [qubits[3], qubits[1]])
    circ << (Ry, qubits[1], lambda x: x[0] / 8)
    circ << (Ry, qubits[0], lambda x: -x[0] / 8)
    circ << (CX, [qubits[2], qubits[1]])
    circ << (CX, [qubits[2], qubits[0]])
    circ << (Ry, qubits[1], lambda x: -x[0] / 8)
    circ << (Ry, qubits[0], lambda x: x[0] / 8)
    circ << (CX, [qubits[3], qubits[1]])
    circ << (H, [qubits[3]])
    circ << (CX, [qubits[0], qubits[3]])
    circ << (Ry, qubits[1], lambda x: -x[0] / 8)
    circ << (Ry, qubits[0], lambda x: x[0] / 8)
    circ << (CX, [qubits[0], qubits[1]])
    circ << (CX, [qubits[2], qubits[0]])
    circ << (H, qubits[0])
    circ << (H, qubits[3])
    circ << (CX, [qubits[0], qubits[2]])
    circ << (CX, [qubits[2], qubits[3]])


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

def construct_circuit(qubits, electrons, params=None,):
    singles, doubles = _excitations(electrons, qubits)
    if params is None:
        params = Parameter([0.0] * (len(singles) + len(doubles)), trainable=True)
    else:
        if not isinstance(params, Parameter):
            raise ValueError(
                f'The params should be type `Parameter`, but got {type(params)}'
            )
        if params.size != len(singles) + len(doubles):
            raise ValueError(
                f'The params size should be 1D and size {len(singles) + len(doubles)}, '
                f'but got size {params.size}'
            )

    state = _hf_state(electrons, qubits)
    qubit_num = qubits
    circ = Circuit(params)
    circ.allocateQubits(qubit_num)
    _basis_state(circ, state)
    for d in doubles:
        _double_excitation(circ, d)
    return circ
