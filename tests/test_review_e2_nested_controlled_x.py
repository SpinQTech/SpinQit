from copy import deepcopy
import unittest

import numpy as np

from spinqit import BasicSimulatorConfig, CX, Circuit, ControlledGate, X, get_basic_simulator, get_compiler


class NestedControlledXRegressionTest(unittest.TestCase):
    def test_adding_two_controls_to_cnot_constructs_and_executes(self):
        gate = ControlledGate(ControlledGate(CX))
        circuit = Circuit()
        qubits = circuit.allocateQubits(4)
        for qubit in qubits[:3]:
            circuit << (X, qubit)
        circuit << (gate, qubits)

        ir = get_compiler('native').compile(circuit, 0)
        result = get_basic_simulator().execute(deepcopy(ir), BasicSimulatorConfig())

        expected = np.zeros(16, dtype=complex)
        expected[15] = 1
        self.assertGreaterEqual(abs(np.vdot(expected, result.states)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
