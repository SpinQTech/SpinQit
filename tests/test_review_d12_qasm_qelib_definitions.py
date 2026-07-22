from copy import deepcopy
import os
import tempfile
import unittest

import numpy as np

from spinqit import (
    BasicSimulatorConfig,
    Circuit,
    Ry,
    X,
    get_basic_simulator,
    get_compiler,
)
from spinqit.backend.qasm_backend import QasmBackend
from spinqit.model import ControlledGate


class QasmQelibDefinitionRegressionTests(unittest.TestCase):
    def test_standard_controlled_gate_is_not_redefined(self):
        circuit = Circuit()
        qubits = circuit.allocateQubits(2)
        circuit << (X, qubits[0])
        circuit << (ControlledGate(Ry), qubits, 0.6)
        ir = get_compiler('native').compile(circuit, 0)

        qasm = QasmBackend.convert_ir_to_qasm(ir)

        self.assertNotIn('gate cry', qasm)
        self.assertIn('cry(0.6) q0[0],q0[1];', qasm)

        with tempfile.NamedTemporaryFile('w', suffix='.qasm', delete=False) as qasm_file:
            qasm_file.write(qasm)
            path = qasm_file.name
        try:
            round_trip_ir = get_compiler('qasm').compile(path, 0)
        finally:
            os.unlink(path)

        self.assertIsNotNone(round_trip_ir)
        simulator = get_basic_simulator()
        expected = np.asarray(
            simulator.execute(deepcopy(ir), BasicSimulatorConfig()).states
        )
        actual = np.asarray(
            simulator.execute(deepcopy(round_trip_ir), BasicSimulatorConfig()).states
        )
        self.assertGreaterEqual(abs(np.vdot(expected, actual)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
