from copy import deepcopy
import unittest

import numpy as np

from spinqit import BasicSimulatorConfig, CCX, Circuit, H, Rz, X, get_basic_simulator, get_compiler
from spinqit.backend.spinq_cloud_backend import SpinQCloudBackend
from spinqit.model.spinqCloud.platform import SQC_25


class CloudRepeatedCcxRegressionTest(unittest.TestCase):
    def test_cloud_decomposition_preserves_operands_after_dag_rewrites(self):
        circuit = Circuit()
        qubits = circuit.allocateQubits(3)
        circuit << (X, qubits[0])
        circuit << (X, qubits[1])
        circuit << (H, qubits[2])
        circuit << (CCX, qubits)
        circuit << (Rz, qubits[2], 0.37)
        circuit << (CCX, qubits)

        ir = get_compiler('native').compile(circuit, 0)
        expected = np.asarray(
            get_basic_simulator().execute(deepcopy(ir), BasicSimulatorConfig()).states
        )

        cloud_ir = deepcopy(ir)
        object.__new__(SpinQCloudBackend).assemble(SQC_25.code, cloud_ir)
        actual = np.asarray(
            get_basic_simulator().execute(cloud_ir, BasicSimulatorConfig()).states
        )

        self.assertGreaterEqual(abs(np.vdot(expected, actual)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
