import os
import tempfile
import unittest

from spinqit import get_compiler
from spinqit.compiler import NodeType


class QasmRegisterBroadcastRegressionTest(unittest.TestCase):
    def test_register_operands_are_paired_elementwise(self):
        source = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
qreg r[2];
cx q,r;
'''
        with tempfile.NamedTemporaryFile('w', suffix='.qasm', delete=False) as qasm_file:
            qasm_file.write(source)
            path = qasm_file.name

        try:
            ir = get_compiler('qasm').compile(path, 0)
        finally:
            os.unlink(path)

        operands = [
            vertex['qubits']
            for vertex in ir.dag.vs
            if vertex['type'] == NodeType.op.value
        ]
        self.assertEqual(operands, [[0, 2], [1, 3]])


if __name__ == '__main__':
    unittest.main()
