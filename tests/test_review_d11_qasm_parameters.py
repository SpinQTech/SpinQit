from copy import deepcopy
from math import pi
import os
import tempfile
import unittest

import numpy as np

from spinqit import (
    BasicSimulatorConfig,
    CX,
    Circuit,
    MatrixGateBuilder,
    Rx,
    Ry,
    Rz,
    X,
    get_basic_simulator,
    get_compiler,
)
from spinqit.backend.qasm_backend import QasmBackend


class QasmParameterRegressionTests(unittest.TestCase):
    @staticmethod
    def controlled_rotation(gate):
        def matrix(params):
            result = np.eye(4, dtype=complex)
            result[2:, 2:] = gate.get_matrix(params[0])
            return result

        builder = MatrixGateBuilder(matrix)
        if gate == Rx:
            builder.append(Rz, [1], lambda *args: pi / 2)
            builder.append(CX, [0, 1])
            builder.append(Ry, [1], lambda params: -params[0] / 2)
            builder.append(CX, [0, 1])
            builder.append(Ry, [1], lambda params: params[0] / 2)
            builder.append(Rz, [1], lambda *args: -pi / 2)
        else:
            builder.append(gate, [1], lambda params: params[0] / 2)
            builder.append(CX, [0, 1])
            builder.append(gate, [1], lambda params: -params[0] / 2)
            builder.append(CX, [0, 1])
        result = builder.to_gate()
        result.label = f'custom_c{gate.label.lower()}'
        return result

    @staticmethod
    def compile_qasm(source):
        with tempfile.NamedTemporaryFile('w', suffix='.qasm', delete=False) as qasm_file:
            qasm_file.write(source)
            path = qasm_file.name
        try:
            return get_compiler('qasm').compile(path, 0)
        finally:
            os.unlink(path)

    def test_controlled_rotation_expressions_survive_qasm_round_trip(self):
        expected_expressions = {
            Rx: ('ry(-a0/2)', 'ry(a0/2)'),
            Ry: ('ry(a0/2)', 'ry(-a0/2)'),
            Rz: ('rz(a0/2)', 'rz(-a0/2)'),
        }
        simulator = get_basic_simulator()

        for gate, expressions in expected_expressions.items():
            with self.subTest(gate=gate.label):
                circuit = Circuit()
                qubits = circuit.allocateQubits(2)
                circuit << (X, qubits[0])
                circuit << (self.controlled_rotation(gate), qubits, 0.6)
                ir = get_compiler('native').compile(circuit, 0)

                qasm = QasmBackend.convert_ir_to_qasm(ir)
                for expression in expressions:
                    self.assertIn(expression, qasm)

                round_trip_ir = self.compile_qasm(qasm)
                self.assertIsNotNone(round_trip_ir)
                expected = np.asarray(
                    simulator.execute(deepcopy(ir), BasicSimulatorConfig()).states
                )
                actual = np.asarray(
                    simulator.execute(deepcopy(round_trip_ir), BasicSimulatorConfig()).states
                )
                self.assertGreaterEqual(abs(np.vdot(expected, actual)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
