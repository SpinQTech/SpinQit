from copy import deepcopy
import os
import tempfile
import unittest

import numpy as np

from spinqit import BasicSimulatorConfig, get_basic_simulator, get_compiler


class QelibCrxRegressionTests(unittest.TestCase):
    def test_crx_definition_matches_controlled_rx_matrix(self):
        angle = 0.6
        source = f'''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
x q[0];
crx({angle}) q[0],q[1];
'''
        with tempfile.NamedTemporaryFile('w', suffix='.qasm', delete=False) as qasm_file:
            qasm_file.write(source)
            path = qasm_file.name
        try:
            ir = get_compiler('qasm').compile(path, 0)
        finally:
            os.unlink(path)

        self.assertIsNotNone(ir)
        state = np.asarray(
            get_basic_simulator().execute(deepcopy(ir), BasicSimulatorConfig()).states
        )
        expected = np.array(
            [0, 0, np.cos(angle / 2), -1j * np.sin(angle / 2)],
            dtype=complex,
        )
        self.assertGreaterEqual(abs(np.vdot(expected, state)) ** 2, 1 - 1e-9)


if __name__ == '__main__':
    unittest.main()
