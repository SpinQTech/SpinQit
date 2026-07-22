import unittest
from unittest.mock import patch

import numpy as np
import torch

from spinqit import QiskitQasmResult
from spinqit.backend.pytorch_backend import TorchResult, TorchSimulatorConfig


class WeightedReadingRegressionTest(unittest.TestCase):
    def assert_weighted_choice(self, result):
        with patch('numpy.random.choice', return_value='0') as choice:
            self.assertEqual(result.get_random_reading(), '0')

        readings = choice.call_args.args[0]
        weights = choice.call_args.kwargs['p']
        self.assertEqual(readings, ['0', '1'])
        np.testing.assert_allclose(weights, [0.9, 0.1])

    def test_qasm_reading_uses_probabilities(self):
        result = QiskitQasmResult()
        result.set_result({'0': 900, '1': 100}, 1000)
        self.assert_weighted_choice(result)

    def test_torch_reading_uses_probabilities(self):
        states = torch.tensor([np.sqrt(0.9), np.sqrt(0.1)], dtype=torch.complex64)
        result = TorchResult(states, TorchSimulatorConfig())
        self.assert_weighted_choice(result)


if __name__ == '__main__':
    unittest.main()
