import unittest

from spinqit import CP, X, Circuit
from spinqit.algorithm.loss import expval
from spinqit.interface.qlayer import QLayer


class PauliMeasurementAfterCompositeRegressionTest(unittest.TestCase):
    @staticmethod
    def build_circuit():
        circuit = Circuit()
        qubits = circuit.allocateQubits(2)
        circuit.allocateClbits(1)
        circuit << (X, qubits[0])
        circuit << (CP, qubits, 0.4)
        return circuit

    def test_pauli_measurement_ignores_definition_subgraphs_when_finding_leaves(self):
        for backend, interface in (('spinq', 'spinq'), ('torch', 'torch')):
            with self.subTest(backend=backend):
                layer = QLayer(
                    self.build_circuit(),
                    expval([('ZZ', 1.0)]),
                    backend_mode=backend,
                    interface=interface,
                    grad_method='backprop' if backend == 'torch' else 'param_shift',
                )

                value = layer()

                self.assertAlmostEqual(float(value), -1.0, places=6)


if __name__ == '__main__':
    unittest.main()
