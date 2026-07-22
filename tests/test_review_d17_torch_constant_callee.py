from copy import deepcopy
import unittest

import numpy as np

from spinqit import (
    BasicSimulatorConfig,
    Circuit,
    H,
    T,
    Td,
    TorchSimulatorConfig,
    X,
    get_basic_simulator,
    get_compiler,
    get_torch_simulator,
)
from spinqit.model import ControlledGate


class TorchConstantCalleeRegressionTests(unittest.TestCase):
    def test_parameterless_controlled_phase_gates_execute(self):
        for gate in (T, Td):
            for level in range(4):
                with self.subTest(gate=gate.label, level=level):
                    circuit = Circuit()
                    qubits = circuit.allocateQubits(2)
                    circuit << (H, qubits[0])
                    circuit << (X, qubits[1])
                    circuit << (ControlledGate(gate), qubits)
                    ir = get_compiler('native').compile(circuit, level)

                    expected = np.asarray(
                        get_basic_simulator().execute(
                            deepcopy(ir), BasicSimulatorConfig()
                        ).states
                    )
                    actual = (
                        get_torch_simulator()
                        .execute(deepcopy(ir), TorchSimulatorConfig())
                        .states.detach().cpu().numpy()
                    )

                    self.assertGreaterEqual(
                        abs(np.vdot(expected, actual)) ** 2,
                        1 - 1e-6,
                    )


if __name__ == '__main__':
    unittest.main()
