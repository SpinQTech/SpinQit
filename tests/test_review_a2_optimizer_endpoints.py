from types import SimpleNamespace
import importlib
import unittest
from unittest.mock import patch

import numpy as np

from spinqit import Parameter
from spinqit.algorithm.optimizer.scipy_optim import ScipyOptimizer
from spinqit.algorithm.optimizer.spsa import SPSAOptimizer


class OptimizerEndpointRegressionTest(unittest.TestCase):
    def test_optimizers_write_endpoint_back_to_parameter(self):
        loss = lambda params: float((params[0] - 3.0) ** 2)
        scipy_module = importlib.import_module('spinqit.algorithm.optimizer.scipy_optim')
        spsa_module = importlib.import_module('spinqit.algorithm.optimizer.spsa')

        scipy_params = Parameter([10.0])
        with patch.object(
            scipy_module,
            'minimize',
            return_value=SimpleNamespace(x=np.array([3.0])),
        ):
            ScipyOptimizer().optimize(loss, scipy_params)

        spsa_params = Parameter([10.0])
        with patch.object(
            spsa_module,
            'minimizeSPSA',
            return_value=SimpleNamespace(x=np.array([3.0])),
        ):
            SPSAOptimizer().optimize(loss, spsa_params)

        np.testing.assert_allclose(scipy_params, [3.0])
        np.testing.assert_allclose(spsa_params, [3.0])


if __name__ == '__main__':
    unittest.main()
