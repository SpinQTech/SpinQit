import math
import unittest

from spinqit import Circuit, Parameter, Ry
from spinqit.algorithm.loss import expval
from spinqit.grad import qgrad
from spinqit.interface.qlayer import QLayer


class PauliQubitOrderRegressionTest(unittest.TestCase):
    def test_first_pauli_character_acts_on_first_circuit_qubit(self):
        circuit = Circuit()
        qubits = circuit.allocateQubits(2)
        theta = circuit.add_params(1)
        circuit << (Ry, qubits[0], theta[0])
        layer = QLayer(
            circuit,
            expval([('ZI', 1.0)]),
            backend_mode='spinq',
            interface='spinq',
            grad_method='param_shift',
        )

        angle = 0.4
        parameter = Parameter([angle])
        value = layer(parameter)
        derivative = qgrad(layer)(parameter)[0]

        self.assertAlmostEqual(value.item(), math.cos(angle), places=7)
        self.assertAlmostEqual(derivative.item(), -math.sin(angle), places=7)


if __name__ == '__main__':
    unittest.main()
