import unittest

import numpy as np

from spinqit.utils.function import schmidt_decompose


class SchmidtDecompositionRegressionTest(unittest.TestCase):
    def test_bell_state_supports_two_by_two_partition(self):
        bell = np.array([1, 0, 0, 1], dtype=float) / np.sqrt(2)
        coefficients, _, _ = schmidt_decompose(bell)
        np.testing.assert_allclose(coefficients, [1 / np.sqrt(2)] * 2)

    def test_rank_deficient_state_keeps_largest_coefficients(self):
        ghz = np.zeros(16)
        ghz[[0, -1]] = 1 / np.sqrt(2)
        coefficients, _, _ = schmidt_decompose(ghz)
        np.testing.assert_allclose(coefficients, [1 / np.sqrt(2)] * 2)


if __name__ == '__main__':
    unittest.main()
