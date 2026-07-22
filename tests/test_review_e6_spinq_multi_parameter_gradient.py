import math
import unittest

from autograd import grad

from spinqit import Circuit, Parameter, Ry, Rz, X
from spinqit.algorithm.loss import expval
from spinqit.grad import qgrad
from spinqit.interface.qlayer import QLayer


class SpinQMultiParameterGradientRegressionTest(unittest.TestCase):
    @staticmethod
    def build_layer():
        circuit = Circuit()
        qubit = circuit.allocateQubits(1)[0]
        alpha = circuit.add_params(1)
        beta = circuit.add_params(1)
        circuit << (Ry, qubit, alpha[0])
        circuit << (Rz, qubit, beta[0])
        return QLayer(
            circuit,
            expval(X.get_matrix()),
            backend_mode='spinq',
            interface='spinq',
            grad_method='adjoint_differentiation',
        )

    def test_first_circuit_argument_has_its_own_vjp(self):
        alpha = Parameter([0.4])
        beta = Parameter([0.3])

        derivative = grad(self.build_layer(), argnum=0)(alpha, beta)

        self.assertEqual(derivative.shape, (1,))
        self.assertAlmostEqual(
            derivative.item(), math.cos(alpha.item()) * math.cos(beta.item()), places=7
        )

    def test_second_circuit_argument_has_its_own_vjp(self):
        alpha = Parameter([0.4])
        beta = Parameter([0.3])

        derivative = grad(self.build_layer(), argnum=1)(alpha, beta)

        self.assertEqual(derivative.shape, (1,))
        self.assertAlmostEqual(
            derivative.item(), -math.sin(alpha.item()) * math.sin(beta.item()), places=7
        )

    def test_qgrad_returns_one_derivative_per_circuit_argument(self):
        alpha = Parameter([0.4])
        beta = Parameter([0.3])

        derivatives = qgrad(self.build_layer())(alpha, beta)

        self.assertEqual(len(derivatives), 2)
        self.assertAlmostEqual(
            derivatives[0].item(),
            math.cos(alpha.item()) * math.cos(beta.item()),
            places=7,
        )
        self.assertAlmostEqual(
            derivatives[1].item(),
            -math.sin(alpha.item()) * math.sin(beta.item()),
            places=7,
        )


if __name__ == '__main__':
    unittest.main()
