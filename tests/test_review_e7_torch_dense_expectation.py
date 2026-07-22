import math
import unittest

import torch

from spinqit import Circuit, Ry, Z
from spinqit.algorithm.loss import expval
from spinqit.interface.qlayer import QLayer


class TorchDenseExpectationRegressionTest(unittest.TestCase):
    def test_dense_hamiltonian_supports_backpropagation(self):
        circuit = Circuit()
        qubit = circuit.allocateQubits(1)[0]
        theta = circuit.add_params(1)
        circuit << (Ry, qubit, theta[0])
        layer = QLayer(
            circuit,
            expval(Z.get_matrix()),
            backend_mode='torch',
            interface='torch',
            grad_method='backprop',
        )

        angle = 0.4
        parameter = torch.tensor([angle], requires_grad=True)
        value = layer(parameter)
        value.backward()

        self.assertAlmostEqual(value.item(), math.cos(angle), places=6)
        self.assertAlmostEqual(parameter.grad.item(), -math.sin(angle), places=6)


if __name__ == '__main__':
    unittest.main()
