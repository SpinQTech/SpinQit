import unittest

from spinqit import Circuit, StateVector, TorchSimulatorConfig, get_compiler, get_torch_simulator


class TorchStateVectorRegressionTest(unittest.TestCase):
    @staticmethod
    def execute(state):
        circuit = Circuit('torch-state-vector')
        qubits = circuit.allocateQubits(1)
        circuit << (StateVector, qubits, state)
        ir = get_compiler('native').compile(circuit, 0)
        return get_torch_simulator().execute(ir, TorchSimulatorConfig())

    def test_norm_uses_complex_magnitude(self):
        valid = self.execute([2 ** -0.5, 1j * 2 ** -0.5])
        self.assertAlmostEqual(float(valid.raw_probabilities.sum().item()), 1.0, places=6)

        with self.assertRaises(ValueError):
            self.execute([2 ** 0.5, 1j])


if __name__ == '__main__':
    unittest.main()
