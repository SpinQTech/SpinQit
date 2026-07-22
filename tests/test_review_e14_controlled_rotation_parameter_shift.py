import math
import unittest

import numpy as np
import torch

from spinqit import Circuit, ControlledGate, H, I, Parameter, Ry, X
from spinqit.algorithm.loss import expval
from spinqit.grad import qgrad
from spinqit.interface.qlayer import QLayer


class ControlledRotationParameterShiftRegressionTest(unittest.TestCase):
    @staticmethod
    def build_circuit():
        circuit = Circuit()
        qubits = circuit.allocateQubits(2)
        theta = circuit.add_params(1)
        circuit << (H, qubits[0])
        circuit << (ControlledGate(Ry), qubits, theta[0])
        return circuit

    @staticmethod
    def hamiltonian():
        return np.kron(X.get_matrix(), I.get_matrix())

    def test_spinq_parameter_shift_handles_controlled_rotation_spectrum(self):
        angle = 0.6
        layer = QLayer(
            self.build_circuit(),
            expval(self.hamiltonian()),
            backend_mode='spinq',
            interface='spinq',
            grad_method='param_shift',
        )
        parameter = Parameter([angle])

        value = layer(parameter)
        derivative = qgrad(layer)(parameter)[0]

        self.assertAlmostEqual(value.item(), math.cos(angle / 2), places=7)
        self.assertAlmostEqual(
            derivative.item(), -math.sin(angle / 2) / 2, places=7
        )

    def test_torch_parameter_shift_handles_controlled_rotation_spectrum(self):
        angle = 0.6
        layer = QLayer(
            self.build_circuit(),
            expval(self.hamiltonian()),
            backend_mode='torch',
            interface='torch',
            grad_method='param_shift',
        )
        parameter = torch.tensor([angle], requires_grad=True)

        value = layer(parameter)
        value.backward()

        self.assertAlmostEqual(value.item(), math.cos(angle / 2), places=6)
        self.assertAlmostEqual(
            parameter.grad.item(), -math.sin(angle / 2) / 2, places=6
        )


if __name__ == '__main__':
    unittest.main()
