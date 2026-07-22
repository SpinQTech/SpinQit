import unittest

import numpy as np

from spinqit.algorithm.qaoa import QAOA


class QaoaCoefficientRegressionTest(unittest.TestCase):
    @staticmethod
    def problem_gate(coefficient):
        qaoa = object.__new__(QAOA)
        qaoa._QAOA__qubit_num = 2
        return qaoa._generate_problem_circuit([('ZZ', coefficient)])

    def test_problem_rotation_scales_by_hamiltonian_coefficient(self):
        angle_1 = self.problem_gate(1.0).factors[0][2]([0.6])
        angle_7 = self.problem_gate(7.0).factors[0][2]([0.6])

        np.testing.assert_allclose(angle_1, [0.6])
        np.testing.assert_allclose(angle_7, [4.2])


if __name__ == '__main__':
    unittest.main()
