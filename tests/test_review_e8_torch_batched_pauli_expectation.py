import unittest

import torch

from spinqit import Circuit, StateVector
from spinqit.algorithm.loss import expval
from spinqit.interface.qlayer import QLayer


class TorchBatchedPauliExpectationRegressionTest(unittest.TestCase):
    def test_pauli_list_returns_one_expectation_per_batched_state(self):
        circuit = Circuit()
        qubit = circuit.allocateQubits(1)[0]
        states = circuit.add_params((2, 2))
        circuit << (StateVector, qubit, states[:])
        layer = QLayer(
            circuit,
            expval([('Z', 1.0)]),
            backend_mode='torch',
            interface='torch',
            grad_method='backprop',
        )

        batch = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
        values = layer(batch)

        self.assertEqual(tuple(values.shape), (2,))
        torch.testing.assert_close(values, torch.tensor([1.0, -1.0]))


if __name__ == '__main__':
    unittest.main()
