from copy import deepcopy
import unittest

import numpy as np

from spinqit import BasicSimulatorConfig, CY, Circuit, H, Rz, X, Z, get_basic_simulator, get_compiler


class BasicSimulatorCyRegressionTest(unittest.TestCase):
    def test_cy_applies_controlled_y_phase(self):
        circuit = Circuit('controlled-y')
        circuit.allocateQubits(2)
        circuit << (H, 0)
        circuit << (CY, [0, 1])

        ir = get_compiler('native').compile(circuit, 0)
        observed = np.asarray(
            get_basic_simulator().execute(deepcopy(ir), BasicSimulatorConfig()).states,
            dtype=complex,
        )
        expected = np.array([1, 0, 0, 1j], dtype=complex) / np.sqrt(2)

        self.assertGreaterEqual(abs(np.vdot(expected, observed)) ** 2, 1 - 1e-9)

    def test_optimizer_rewrites_do_not_reverse_cy_operands(self):
        circuit = Circuit('optimized-controlled-y')
        circuit.allocateQubits(2)
        circuit << (Rz, 0, 0.2)
        circuit << (Z, 0)
        circuit << (X, 1)
        circuit << (CY, [0, 1])

        compiler = get_compiler('native')
        config = BasicSimulatorConfig()

        def simulate(level):
            ir = compiler.compile(circuit, level)
            state = np.asarray(get_basic_simulator().execute(deepcopy(ir), config).states)
            return state / np.linalg.norm(state)

        reference = simulate(0)
        candidate = simulate(1)
        self.assertGreaterEqual(abs(np.vdot(reference, candidate)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
