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
    H,
    TorchSimulatorConfig,
    X,
    get_basic_simulator,
    get_compiler,
    get_torch_simulator,
)
from spinqit.backend.qasm_backend import QasmBackend
from spinqit.backend.spinq_cloud_backend import SpinQCloudBackend
from spinqit.model.spinqCloud.platform import SQC_25


class NestedControlledHadamardRegressionTest(unittest.TestCase):
    @staticmethod
    def build_circuit():
        circuit = Circuit()
        qubits = circuit.allocateQubits(3)
        circuit << (X, qubits[1])
        circuit << (H, qubits[0])
        circuit << (ControlledGate(ControlledGate(H)), qubits)
        return circuit

    @staticmethod
    def assert_expected_state(states, tolerance=1e-8):
        expected = np.zeros(8, dtype=complex)
        expected[2] = 1 / np.sqrt(2)
        expected[6] = 0.5
        expected[7] = 0.5
        states = np.asarray(states)
        if states.ndim > 1:
            states = states[0]
        assert abs(np.vdot(expected, states)) ** 2 >= 1 - tolerance

    @staticmethod
    def compile_qasm(source):
        with tempfile.NamedTemporaryFile('w', suffix='.qasm', delete=False) as qasm_file:
            qasm_file.write(source)
            path = qasm_file.name
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                return get_compiler('qasm').compile(path, 0)
        finally:
            os.unlink(path)

    def test_nested_control_preserves_hadamard_phase_on_all_lowering_paths(self):
        ir = get_compiler('native').compile(self.build_circuit(), 0)

        basic = get_basic_simulator().execute(deepcopy(ir), BasicSimulatorConfig())
        self.assert_expected_state(basic.states)

        torch = get_torch_simulator().execute(deepcopy(ir), TorchSimulatorConfig())
        self.assert_expected_state(torch.states.detach().cpu().numpy(), tolerance=1e-6)

        qasm_ir = self.compile_qasm(QasmBackend.convert_ir_to_qasm(ir))
        qasm = get_basic_simulator().execute(qasm_ir, BasicSimulatorConfig())
        self.assert_expected_state(qasm.states)

        cloud_ir = deepcopy(ir)
        object.__new__(SpinQCloudBackend).assemble(SQC_25.code, cloud_ir)
        cloud = get_basic_simulator().execute(cloud_ir, BasicSimulatorConfig())
        self.assert_expected_state(cloud.states)


if __name__ == '__main__':
    unittest.main()
