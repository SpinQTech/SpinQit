import unittest

from spinqit import Circuit, CircuitOperationValidationError, X, get_compiler
from spinqit.backend.spinq_cloud_backend import SpinQCloudBackend


class CloudConditionRegressionTest(unittest.TestCase):
    def test_cloud_rejects_unsupported_classical_condition(self):
        circuit = Circuit('conditional-cloud-gate')
        circuit.allocateQubits(1)
        circuit.allocateClbits(1)
        circuit << (X, 0)
        circuit | ([0], '==', 1)
        ir = get_compiler('native').compile(circuit, 0)

        backend = object.__new__(SpinQCloudBackend)
        with self.assertRaises(CircuitOperationValidationError):
            backend.assemble('offline', ir)


if __name__ == '__main__':
    unittest.main()
