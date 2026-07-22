import math
import unittest

import numpy as np

from spinqit import CP, H, X, Circuit, Parameter
from spinqit.algorithm.loss import expval
from spinqit.grad import qgrad
from spinqit.interface.qlayer import QLayer


class AdjointControlledPhaseRegressionTest(unittest.TestCase):
    @staticmethod
    def build_layer():
        circuit = Circuit()
        qubits = circuit.allocateQubits(2)
        theta = circuit.add_params(1)
        circuit << (X, qubits[0])
        circuit << (H, qubits[1])
        circuit << (CP, qubits, theta[0])
        circuit << (H, qubits[1])

        projector_10 = np.diag([0.0, 0.0, 1.0, 0.0])
        return QLayer(
            circuit,
            expval(projector_10),
            backend_mode='spinq',
            interface='spinq',
            grad_method='adjoint_differentiation',
        )

    def test_adjoint_descends_into_parameterized_controlled_gate(self):
        angle = 0.4
        theta = Parameter([angle])
        layer = self.build_layer()

        value = layer(theta)
        gradient = qgrad(layer)(theta)[0]

        self.assertAlmostEqual(value.item(), (1 + math.cos(angle)) / 2, places=7)
        self.assertAlmostEqual(gradient.item(), -math.sin(angle) / 2, places=7)


if __name__ == '__main__':
    unittest.main()
