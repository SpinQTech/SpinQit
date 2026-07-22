import unittest

import numpy as np

from spinqit.algorithm import QAOA, VQE
from spinqit.grad import qgrad


class OneGradientOptimizer:
    def __init__(self):
        self.gradient = None

    def optimize(self, layer, *params):
        gradient_fn = qgrad(layer)
        self.gradient = gradient_fn(*params)
        return [gradient_fn.forward]


class VariationalListHamiltonianRegressionTest(unittest.TestCase):
    def test_vqe_default_adjoint_accepts_documented_list_hamiltonian(self):
        optimizer = OneGradientOptimizer()
        vqe = VQE([('Z', 1.0)], optimizer, depth=1)

        losses = vqe.run()

        self.assertEqual(len(losses), 1)
        self.assertTrue(np.isfinite(losses[0]))
        self.assertEqual(optimizer.gradient[0].shape, vqe.optimized_params.shape)
        self.assertIsInstance(vqe.hamiltonian, list)

    def test_qaoa_default_adjoint_accepts_documented_list_hamiltonian(self):
        optimizer = OneGradientOptimizer()
        qaoa = QAOA([('Z', 1.0)], optimizer, depth=1)

        losses = qaoa.run()

        self.assertEqual(len(losses), 1)
        self.assertTrue(np.isfinite(losses[0]))
        self.assertEqual(optimizer.gradient[0].shape, qaoa.optimized_params.shape)
        self.assertIsInstance(qaoa.hamiltonian, list)


if __name__ == '__main__':
    unittest.main()
