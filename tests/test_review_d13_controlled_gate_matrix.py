import unittest

import numpy as np

from spinqit import Ry
from spinqit.model import ControlledGate


class ControlledGateMatrixRegressionTests(unittest.TestCase):
    def test_controlled_gate_matrix_uses_square_zero_blocks(self):
        angle = 0.6
        rotation = Ry.get_matrix(angle)
        expected = np.zeros((4, 4), dtype=complex)
        expected[:2, :2] = np.eye(2)
        expected[2:, 2:] = rotation

        controlled = ControlledGate(Ry)
        np.testing.assert_allclose(controlled.get_matrix(angle), expected)

        nested_expected = np.zeros((8, 8), dtype=complex)
        nested_expected[:4, :4] = np.eye(4)
        nested_expected[4:, 4:] = expected
        np.testing.assert_allclose(
            ControlledGate(controlled).get_matrix(angle),
            nested_expected,
        )


if __name__ == '__main__':
    unittest.main()
