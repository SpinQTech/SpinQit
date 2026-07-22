import unittest

import numpy as np

from spinqit import BasicSimulatorConfig, Circuit, X, Y, Z, get_basic_simulator, get_compiler
from spinqit.algorithm.qaoa import QAOA


class QaoaMixedPauliRegressionTest(unittest.TestCase):
    def test_mixed_pauli_problem_terms_act_on_every_nonidentity_qubit(self):
        angle = 0.6
        matrices = {'X': X.get_matrix(), 'Y': Y.get_matrix(), 'Z': Z.get_matrix()}

        for term in ('XZ', 'YZ', 'XY'):
            with self.subTest(term=term):
                qaoa = object.__new__(QAOA)
                qaoa._QAOA__qubit_num = 2
                problem_gate = qaoa._generate_problem_circuit([(term, 1.0)])

                circuit = Circuit('mixed-pauli')
                qubits = circuit.allocateQubits(2)
                circuit << (problem_gate, qubits, angle)
                state = np.asarray(
                    get_basic_simulator().execute(
                        get_compiler('native').compile(circuit, 0),
                        BasicSimulatorConfig(),
                    ).states,
                    dtype=complex,
                )

                pauli = np.kron(matrices[term[0]], matrices[term[1]])
                initial = np.array([1, 0, 0, 0], dtype=complex)
                expected = (
                    np.cos(angle / 2) * np.eye(4)
                    - 1j * np.sin(angle / 2) * pauli
                ) @ initial
                self.assertGreaterEqual(abs(np.vdot(expected, state)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
