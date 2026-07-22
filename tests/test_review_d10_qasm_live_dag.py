import unittest

import numpy as np

from spinqit import Circuit, H, MatrixGateBuilder, get_compiler
from spinqit.backend.qasm_backend import QasmBackend
from spinqit.compiler.ir import NodeType
from spinqit.model import ControlledGate


class QasmLiveDagRegressionTests(unittest.TestCase):
    def test_optimized_composite_gate_invocation_is_serialized(self):
        for level in (0, 1, 2, 3):
            with self.subTest(level=level):
                matrix = np.eye(4, dtype=complex)
                matrix[2:, 2:] = H.get_matrix()
                builder = MatrixGateBuilder(matrix)
                for factor in ControlledGate(H).factors:
                    builder.append(factor[0], factor[1])
                gate = builder.to_gate()
                gate.label = 'custom_ch'
                circuit = Circuit()
                circuit.allocateQubits(2)
                circuit.allocateClbits(1)
                circuit << (gate, [0, 1])
                circuit | ([0], '==', 1)

                ir = get_compiler('native').compile(circuit, level)
                qasm = QasmBackend.convert_ir_to_qasm(ir)

                self.assertIn('if (c0==1) custom_ch q0[0],q0[1];', qasm.splitlines())
                definition = next(
                    vertex for vertex in ir.dag.vs
                    if vertex['type'] == NodeType.definition.value
                    and vertex['name'] == 'custom_ch'
                )
                callee_count = sum(
                    ir.dag.vs[index]['type'] == NodeType.callee.value
                    for index in ir.dag.subcomponent(definition.index, mode='out')
                )
                body = qasm.split('{\n', 1)[1].split('}\n', 1)[0].splitlines()
                self.assertEqual(len(body), callee_count)
                self.assertNotIn('custom_ch qb0,qb1;', body)


if __name__ == '__main__':
    unittest.main()
