from copy import deepcopy
import contextlib
import io
import os
import tempfile
import unittest

import numpy as np

from spinqit import (
    BasicSimulatorConfig,
    Circuit,
    ControlledGate,
    MatrixGateBuilder,
    TorchSimulatorConfig,
    X,
    get_basic_simulator,
    get_compiler,
    get_torch_simulator,
)
from spinqit.backend.qasm_backend import QasmBackend


class ControlledMatrixGateRegressionTest(unittest.TestCase):
    @staticmethod
    def build_circuit():
        matrix_x = MatrixGateBuilder(X.get_matrix()).to_gate()
        circuit = Circuit()
        qubits = circuit.allocateQubits(2)
        circuit << (X, qubits[0])
        circuit << (ControlledGate(matrix_x), qubits)
        return circuit

    @staticmethod
    def assert_target_flipped(states):
        expected = np.zeros(4, dtype=complex)
        expected[3] = 1
        states = np.asarray(states)
        if states.ndim > 1:
            states = states[0]
        assert abs(np.vdot(expected, states)) ** 2 >= 1 - 1e-6

    def test_controlled_matrix_gate_executes_on_all_local_lowering_paths(self):
        ir = get_compiler('native').compile(self.build_circuit(), 0)

        basic_result = get_basic_simulator().execute(deepcopy(ir), BasicSimulatorConfig())
        self.assert_target_flipped(basic_result.states)

        torch_result = get_torch_simulator().execute(deepcopy(ir), TorchSimulatorConfig())
        self.assert_target_flipped(torch_result.states.detach().cpu().numpy())

        qasm = QasmBackend.convert_ir_to_qasm(ir)
        with tempfile.NamedTemporaryFile('w', suffix='.qasm', delete=False) as qasm_file:
            qasm_file.write(qasm)
            path = qasm_file.name
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                qasm_ir = get_compiler('qasm').compile(path, 0)
        finally:
            os.unlink(path)
        qasm_result = get_basic_simulator().execute(qasm_ir, BasicSimulatorConfig())
        self.assert_target_flipped(qasm_result.states)


if __name__ == '__main__':
    unittest.main()
