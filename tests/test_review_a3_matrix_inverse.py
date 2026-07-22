import unittest

import numpy as np

from spinqit import Circuit, H, InverseBuilder, MatrixGateBuilder, Z, get_compiler
from spinqit.primitive import AmplitudeAmplification


class MatrixGateInverseRegressionTest(unittest.TestCase):
    def test_factorless_matrix_gate_has_conjugate_transpose_inverse(self):
        gate = MatrixGateBuilder(H.get_matrix()).to_gate()

        inverse = InverseBuilder(gate).to_gate()

        self.assertIsNotNone(inverse)
        np.testing.assert_allclose(inverse.get_matrix(), H.get_matrix().conj().T)

    def test_matrix_state_operator_builds_one_qubit_amplitude_amplification(self):
        state_operator = MatrixGateBuilder(H.get_matrix()).to_gate()

        instructions = AmplitudeAmplification(
            Z,
            [0],
            state_operator=state_operator,
            state_qubits=[0],
        ).build()
        circuit = Circuit('one-qubit-amplitude-amplification')
        circuit.allocateQubits(1)
        circuit.extend(instructions)

        get_compiler('native').compile(circuit, 0)


if __name__ == '__main__':
    unittest.main()
