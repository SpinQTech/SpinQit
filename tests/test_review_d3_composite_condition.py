import unittest

from spinqit import Circuit, H, get_compiler
from spinqit.compiler import NodeType
from spinqit.model import ControlledGate


class CompositeConditionRegressionTest(unittest.TestCase):
    def test_controlled_composite_gate_keeps_classical_condition(self):
        circuit = Circuit('conditional-controlled-h')
        circuit.allocateQubits(2)
        circuit.allocateClbits(1)
        circuit << (ControlledGate(H), [0, 1])
        circuit | ([0], '==', 1)

        ir = get_compiler('native').compile(circuit, 0)
        caller = next(
            vertex
            for vertex in ir.dag.vs
            if vertex['type'] == NodeType.caller.value
        )

        self.assertEqual(caller['cmp'], 0)
        self.assertEqual(caller['constant'], 1)
        self.assertEqual(ir.get_conbits(caller.index), [0])


if __name__ == '__main__':
    unittest.main()
