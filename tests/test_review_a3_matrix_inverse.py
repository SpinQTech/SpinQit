import unittest

import numpy as np

from spinqit import H, InverseBuilder, MatrixGateBuilder


class MatrixGateInverseRegressionTest(unittest.TestCase):
    def test_factorless_matrix_gate_has_conjugate_transpose_inverse(self):
        gate = MatrixGateBuilder(H.get_matrix()).to_gate()

        inverse = InverseBuilder(gate).to_gate()

        self.assertIsNotNone(inverse)
        np.testing.assert_allclose(inverse.get_matrix(), H.get_matrix().conj().T)


if __name__ == '__main__':
    unittest.main()
