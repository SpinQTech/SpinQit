import unittest

from spinqit import (
    Circuit,
    H,
    TorchSimulatorConfig,
    X,
    get_compiler,
    get_torch_simulator,
)
from spinqit.model import ControlledGate


class TorchOptimizedCompositeRegressionTests(unittest.TestCase):
    def test_numeric_optimized_callee_parameters_are_executed(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                circuit = Circuit()
                qubits = circuit.allocateQubits(2)
                circuit << (X, qubits[0])
                circuit << (ControlledGate(H), qubits)
                ir = get_compiler('native').compile(circuit, level)

                result = get_torch_simulator().execute(ir, TorchSimulatorConfig())

                self.assertAlmostEqual(result.probabilities['10'], 0.5, places=6)
                self.assertAlmostEqual(result.probabilities['11'], 0.5, places=6)


if __name__ == '__main__':
    unittest.main()
