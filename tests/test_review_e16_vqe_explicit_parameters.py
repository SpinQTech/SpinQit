import unittest

import numpy as np

from spinqit.algorithm import VQE


class VqeExplicitParametersRegressionTest(unittest.TestCase):
    def test_default_ansatz_accepts_explicit_initial_parameters(self):
        initial = np.zeros((1, 1, 3))

        vqe = VQE([('Z', 1.0)], object(), params=initial, depth=1)

        self.assertEqual(vqe.circuit.qubits_num, 1)
        np.testing.assert_array_equal(vqe.optimized_params, initial)

    def test_default_ansatz_accepts_explicit_parameter_shape(self):
        vqe = VQE([('Z', 1.0)], object(), params=(1, 1, 3), depth=1)

        self.assertEqual(vqe.circuit.qubits_num, 1)
        self.assertEqual(vqe.optimized_params.shape, (1, 1, 3))


if __name__ == '__main__':
    unittest.main()
