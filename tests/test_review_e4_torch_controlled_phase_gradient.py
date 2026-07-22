import math
import unittest

import torch

from spinqit import CP, H, X, Circuit
from spinqit.algorithm.loss import probs
from spinqit.interface.qlayer import QLayer


class TorchControlledPhaseGradientRegressionTest(unittest.TestCase):
    @staticmethod
    def build_circuit():
        circuit = Circuit()
        qubits = circuit.allocateQubits(2)
        theta = circuit.add_params(1)
        circuit << (X, qubits[0])
        circuit << (H, qubits[1])
        circuit << (CP, qubits, theta[0])
        circuit << (H, qubits[1])
        return circuit

    def test_trainable_controlled_phase_compiles_and_backpropagates(self):
        angle = 0.4
        for level in range(4):
            with self.subTest(level=level):
                layer = QLayer(
                    self.build_circuit(),
                    probs(),
                    backend_mode='torch',
                    interface='torch',
                    grad_method='backprop',
                    optimization_level=level,
                )
                theta = torch.tensor([angle], dtype=torch.float64, requires_grad=True)
                probability = layer(theta)[2]
                probability.backward()

                self.assertAlmostEqual(
                    probability.item(), (1 + math.cos(angle)) / 2, places=6
                )
                self.assertAlmostEqual(
                    theta.grad.item(), -math.sin(angle) / 2, places=6
                )


if __name__ == '__main__':
    unittest.main()
