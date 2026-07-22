import unittest

import numpy as np

from spinqit import Rz
from spinqit.algorithm import QAOA
from spinqit.grad import qgrad


class OneGradientOptimizer:
    def __init__(self):
        self.gradient = None

    def optimize(self, layer, *params):
        gradient_fn = qgrad(layer)
        self.gradient = gradient_fn(*params)
        return [gradient_fn.forward]


class QaoaCustomProblemAnsatzRegressionTest(unittest.TestCase):
    def test_custom_problem_ansatz_uses_problem_qubit_count(self):
        optimizer = OneGradientOptimizer()
        qaoa = QAOA(
            [('Z', 1.0)],
            optimizer,
            depth=1,
            problem_ansatz=Rz,
        )

        losses = qaoa.run()

        self.assertEqual(qaoa.circuit.qnum, 1)
        self.assertEqual(len(losses), 1)
        self.assertTrue(np.isfinite(losses[0]))
        self.assertEqual(optimizer.gradient[0].shape, qaoa.optimized_params.shape)


if __name__ == '__main__':
    unittest.main()
