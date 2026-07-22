from copy import deepcopy
import unittest

import numpy as np

from spinqit import BasicSimulatorConfig, Circuit, Ry, SWAP, X, get_basic_simulator, get_compiler


class PureStateSwapRegressionTest(unittest.TestCase):
    def test_level_three_preserves_state_across_swaps(self):
        circuit = Circuit('pure-state-swap')
        circuit.allocateQubits(2)
        circuit << (Ry, 0, 0.3)
        circuit << (Ry, 1, 0.3)
        circuit << (SWAP, [0, 1])
        circuit << (Ry, 0, 0.4)
        circuit << (SWAP, [0, 1])
        circuit << (X, 0)

        compiler = get_compiler('native')
        config = BasicSimulatorConfig()

        def simulate(level):
            ir = compiler.compile(circuit, level)
            state = np.asarray(get_basic_simulator().execute(deepcopy(ir), config).states)
            return state / np.linalg.norm(state)

        reference = simulate(0)
        candidate = simulate(3)
        self.assertGreaterEqual(abs(np.vdot(reference, candidate)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
