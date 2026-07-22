from copy import deepcopy
import unittest

import numpy as np

from spinqit import BasicSimulatorConfig, CY, Circuit, ControlledGate, X, get_basic_simulator, get_compiler


class ControlledCyRegressionTest(unittest.TestCase):
    def test_adding_a_control_to_cy_controls_both_existing_qubits(self):
        circuit = Circuit()
        qubits = circuit.allocateQubits(3)
        circuit << (X, qubits[0])
        circuit << (X, qubits[1])
        circuit << (ControlledGate(CY), qubits)

        ir = get_compiler('native').compile(circuit, 0)
        result = get_basic_simulator().execute(deepcopy(ir), BasicSimulatorConfig())

        expected = np.zeros(8, dtype=complex)
        expected[7] = 1j
        self.assertGreaterEqual(abs(np.vdot(expected, result.states)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
