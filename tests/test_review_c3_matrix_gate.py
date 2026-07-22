from copy import deepcopy
import unittest

import numpy as np

from spinqit import BasicSimulatorConfig, Circuit, MatrixGateBuilder, get_basic_simulator, get_compiler


class MatrixGateRegressionTest(unittest.TestCase):
    def test_factorless_matrix_gate_executes_on_basic_simulator(self):
        matrix_x = MatrixGateBuilder(np.array([[0, 1], [1, 0]], dtype=complex)).to_gate()
        matrix_x.label = 'matrix_x'
        circuit = Circuit('matrix-x')
        circuit.allocateQubits(1)
        circuit << (matrix_x, 0)

        ir = get_compiler('native').compile(circuit, 0)
        result = get_basic_simulator().execute(deepcopy(ir), BasicSimulatorConfig())

        self.assertAlmostEqual(result.probabilities.get('1', 0.0), 1.0)

    def test_factorless_two_qubit_matrix_gate_executes_on_basic_simulator(self):
        random = np.random.default_rng(7)
        raw = random.normal(size=(4, 4)) + 1j * random.normal(size=(4, 4))
        matrix, _ = np.linalg.qr(raw)
        matrix_gate = MatrixGateBuilder(matrix).to_gate()
        matrix_gate.label = 'matrix_two_qubit'
        circuit = Circuit('matrix-two-qubit')
        qubits = circuit.allocateQubits(2)
        circuit << (matrix_gate, qubits)

        ir = get_compiler('native').compile(circuit, 0)
        result = get_basic_simulator().execute(deepcopy(ir), BasicSimulatorConfig())

        state = np.asarray(result.states)
        self.assertGreaterEqual(abs(np.vdot(matrix[:, 0], state)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
