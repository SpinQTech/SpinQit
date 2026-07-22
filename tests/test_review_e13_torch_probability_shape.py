import unittest
import warnings

from spinqit import Circuit, H, TorchSimulatorConfig, get_compiler, get_torch_simulator


class TorchProbabilityShapeRegressionTest(unittest.TestCase):
    def test_probability_dimension_does_not_convert_numpy_array_to_scalar(self):
        circuit = Circuit()
        qubit = circuit.allocateQubits(1)[0]
        circuit << (H, qubit)
        result = get_torch_simulator().execute(
            get_compiler('native').compile(circuit, 0),
            TorchSimulatorConfig(),
        )

        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            probabilities = result.raw_probabilities

        self.assertEqual(tuple(probabilities.shape), (2,))
        self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=6)


if __name__ == '__main__':
    unittest.main()
