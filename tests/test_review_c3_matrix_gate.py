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


if __name__ == '__main__':
    unittest.main()
