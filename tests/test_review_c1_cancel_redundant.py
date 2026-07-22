from copy import deepcopy
import unittest

import numpy as np

from spinqit import BasicSimulatorConfig, Circuit, H, I, Rx, X, get_basic_simulator, get_compiler


class CancelRedundantGateRegressionTest(unittest.TestCase):
    def test_identity_does_not_join_preceding_cancellation_path(self):
        compiler = get_compiler('native')
        config = BasicSimulatorConfig()

        for gate in (H, X):
            with self.subTest(gate=gate.label):
                circuit = Circuit('gate-then-identity')
                circuit.allocateQubits(1)
                circuit << (gate, 0)
                circuit << (I, 0)

                reference = get_basic_simulator().execute(
                    deepcopy(compiler.compile(circuit, 0)), config
                ).states
                candidate = get_basic_simulator().execute(
                    deepcopy(compiler.compile(circuit, 1)), config
                ).states

                self.assertGreaterEqual(
                    abs(np.vdot(reference, candidate)) ** 2,
                    1 - 1e-9,
                )

    def test_mixed_cancellations_compile_and_preserve_state(self):
        circuit = Circuit('mixed-cancellations')
        circuit.allocateQubits(1)
        circuit << (H, 0)
        circuit << (H, 0)
        circuit << (Rx, 0, 0.2)
        circuit << (Rx, 0, 0.3)
        circuit << (X, 0)

        compiler = get_compiler('native')
        config = BasicSimulatorConfig()

        def simulate(level):
            ir = compiler.compile(circuit, level)
            state = np.asarray(get_basic_simulator().execute(deepcopy(ir), config).states)
            return state / np.linalg.norm(state)

        reference = simulate(0)
        for level in (1, 2, 3):
            with self.subTest(level=level):
                candidate = simulate(level)
                self.assertGreaterEqual(abs(np.vdot(reference, candidate)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
