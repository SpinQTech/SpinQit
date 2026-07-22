import contextlib
import io
import os
import tempfile
import unittest

from spinqit import get_compiler
from spinqit.compiler import NodeType


class QasmRegisterBroadcastRegressionTest(unittest.TestCase):
    @staticmethod
    def compile_source(source):
        with tempfile.NamedTemporaryFile('w', suffix='.qasm', delete=False) as qasm_file:
            qasm_file.write(source)
            path = qasm_file.name

        try:
            return get_compiler('qasm').compile(path, 0)
        finally:
            os.unlink(path)

    def test_mismatched_full_register_sizes_are_rejected(self):
        source = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
qreg r[2];
cx q,r;
'''
        with contextlib.redirect_stderr(io.StringIO()):
            ir = self.compile_source(source)
        self.assertIsNone(ir)

    def test_register_operands_are_paired_elementwise(self):
        source = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
qreg r[2];
cx q,r;
'''
        ir = self.compile_source(source)

        operands = [
            vertex['qubits']
            for vertex in ir.dag.vs
            if vertex['type'] == NodeType.op.value
        ]
        self.assertEqual(operands, [[0, 2], [1, 3]])


if __name__ == '__main__':
    unittest.main()
