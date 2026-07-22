import unittest

import numpy as np

from spinqit import Circuit, H, QiskitQasmResult
from spinqit.algorithm.loss import probs
from spinqit.interface.qlayer import QLayer


class QasmProbabilityRegressionTest(unittest.TestCase):
    def test_probability_measurement_uses_qasm_config_measure_qubits(self):
        def executor(_qasm, shots):
            result = QiskitQasmResult()
            result.set_result({'0': shots}, shots)
            return result

        circuit = Circuit('qasm-probabilities')
        circuit.allocateQubits(1)
        circuit << (H, 0)
        layer = QLayer(circuit, probs(), backend_mode='qasm', backend_fn=executor)

        np.testing.assert_allclose(layer(), [1.0, 0.0])


if __name__ == '__main__':
    unittest.main()
